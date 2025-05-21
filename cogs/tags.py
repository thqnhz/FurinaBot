"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import asqlite
from discord.ext import commands

from core import FurinaCog, FurinaCtx
from core.sql import TagSQL
from core.views import PaginatedView

if TYPE_CHECKING:
    from discord import Message

    from core import FurinaBot


class Tags(FurinaCog):
    """Tags Related Commands"""
    async def cog_load(self) -> None:
        self.pool: TagSQL = TagSQL(await asqlite.create_pool(Path() / 'db' / 'tags.db'))
        await self.pool.create_tables()
        return await super().cog_load()

    @commands.hybrid_group(name='tag', fallback='get')
    async def tag_group(self, ctx: FurinaCtx, *, name: str) -> None:
        """Get a tag by name

        Tag is a silly text that is **user** created.
        Sometimes it is useful and sometime it's not.
        You can create your own tag with `/tag create` command.

        Parameters
        ----------
        name : str
            - Name of the tag
        """
        tag_content = await self.pool.fetchval(
            """
            SELECT t.content FROM tags t WHERE t.name = ? and t.guild_id = ?
            UNION
            SELECT t.content FROM tags t
            JOIN tag_aliases ta ON t.guild_id = ta.guild_id and t.name = ta.name
            WHERE t.guild_id = ? AND (t.name = ? OR ta.alias = ?)
            """,
            name,
            ctx.guild.id,
            ctx.guild.id,
            name,
            name
        )
        if not tag_content:
            await ctx.send(f"No tags found for query: `{name}`")
        else:
            await ctx.send(tag_content)

    @tag_group.command(name='create')
    async def tag_create(self,
                         ctx: FurinaCtx,
                         name: str | None = None,
                         *,
                         content: str | None = None) -> None:
        """Create a tag

        Tag name/content cannot contain the bot's prefix or mention.
        To make a name that contains spaces, wrap it in quotes.
        Can be create "interactively" when not specify either name or content. Or neither.

        Parameters
        ----------
        name : str, optional
            Name of the tag
        content : str, optional
            Content of the tag
        """
        def check(m: Message) -> bool:
            return (m.author == ctx.author and
                    m.channel == ctx.channel and
                    m.content and not
                    m.content.startswith(tuple(self.bot.get_pre(self.bot, m))))
        # tag create /BLANK/
        if not name:
            try:
                await ctx.send(
                    "What is the name of the tag\n-# Type 'cancel' to cancel tag creation"
                )
                name_input: Message = await self.bot.wait_for("message", check=check, timeout=30)
                name = name_input.content
            except asyncio.TimeoutError:
                await ctx.reply("No user input, cancelling tag creation")
        name = name.lower().replace('"', '').replace("'", "")
        if name == 'cancel':
            await ctx.send("Cancelling tag creation")
            return
        if content:
            content = await commands.clean_content().convert(ctx, content)
        # tag create <name> /BLANK/
        if name and not content:
            try:
                await ctx.send("What is the content of the tag?")
                content_input: Message = await self.bot.wait_for("message",
                                                                 check=check,
                                                                 timeout=120)
                content = content_input.clean_content
            except asyncio.TimeoutError:
                await ctx.reply("No user input, cancelling tag creation")
        if content.lower() == 'cancel':
            await ctx.send("Cancelling tag creation")
            return
        # tag create <name> <content>
        if not self.__name_check(ctx, name):
            await ctx.send("Invalid tag name")
            return
        check_exist = await self.__check_tag_name(ctx, name)
        if check_exist:
            await ctx.send(f"Tag `{name}` already exists")
            return
        await self.pool.execute(
            """
            INSERT INTO tags (guild_id, owner, name, content)
            VALUES (?, ?, ?, ?)
            """,
            ctx.guild.id,
            ctx.author.id,
            name,
            content
        )
        await ctx.send(f"Created tag `{name}`")

    def __name_check(self, ctx: FurinaCtx, name: str) -> bool:
        """Simple check if the name does not start with the bot's prefix or mention"""
        return not name.lower().startswith((self.get_prefix(ctx), self.bot.user.mention))

    async def __check_tag_name(self, ctx: FurinaCtx, name: str) -> bool:
        """Database checking if a tag name exists"""
        fetched = await self.pool.fetchval(
            """
            SELECT t.content FROM tags t WHERE t.name = ? and t.guild_id = ?
            UNION
            SELECT t.content FROM tags t
            JOIN tag_aliases ta ON t.guild_id = ta.guild_id and t.name = ta.name
            WHERE t.guild_id = ? AND (t.name = ? OR ta.alias = ?)
            """,
            name,
            ctx.guild.id,
            ctx.guild.id,
            name,
            name
        )
        return fetched is not None

    @tag_group.command(name='delete', aliases=['del'])
    async def tag_delete(self, ctx: FurinaCtx, *, name: str) -> None:
        """Delete a tag by name

        Delete a tag with provided name.
        You can only delete your own tag.
        However if you have `Manage Server` permission you can force delete a tag.

        Parameters
        ----------
        name : str
            Name of the tag
        """
        name = name.lower().replace('"', '').replace("'", "")
        if ctx.author.guild_permissions.manage_guild:
            result = await self.__force_delete_tag(guild_id=ctx.guild.id, name=name)
        else:
            result = await self.__delete_tag(guild_id=ctx.guild.id, owner=ctx.author.id, name=name)
        await ctx.send(result)

    async def __force_delete_tag(self, *, guild_id: int, name: str) -> str:
        """Forcefully delete a tag and its aliases from the database"""
        deleted = await self.pool.fetchone(
            """
            DELETE FROM tags
            WHERE guild_id = ? AND name = ?
            RETURNING *
            """,
            guild_id,
            name
        )
        if deleted is None:
            deleted = await self.pool.fetchone(
                """
                DELETE FROM tag_aliases
                WHERE guild_id = ? AND alias = ?
                """,
                guild_id,
                name
            )
        else:
            await self.pool.execute(
                """
                DELETE FROM tag_aliases
                WHERE guild_id = ? AND name = ?
                """,
                guild_id,
                name
            )
        if deleted is None:
            return f"No tags or aliases with query `{name}` for deletion"
        return f"Deleted tag `{name}`!"

    async def __delete_tag(self, *, guild_id: int, owner: int, name: str) -> str:
        """Check if the user is the owner of the tag and force delete it"""
        tag_owner: int = await self.pool.fetchval(
            """
            SELECT owner FROM tags
            WHERE guild_id = ? AND name = ?
            """,
            guild_id,
            name
        )
        if tag_owner != owner:
            return "You do not own this tag!"
        return await self.__force_delete_tag(guild_id=guild_id, name=name)

    @tag_group.command(name='alias')
    async def tag_alias(self, ctx: FurinaCtx, alias: str, *, name: str) -> None:
        """Create a tag alias

        A tag alias points to the original tag.
        If the original tag content changes, the alias content is too.
        If the original tag is deleted, the alias is also deleted.

        Parameters
        ----------
        alias : str
            Name of the alias
        name : str
            Name of the tag
        """
        check_alias_exist = await self.__check_tag_name(ctx, alias)
        if check_alias_exist:
            await ctx.send(f"Tag `{alias}` already exists")
            return
        check_name_exist = await self.__check_tag_name(ctx, name)
        if not check_name_exist:
            await ctx.send(f"Cannot create alias for non-existent tag `{name}`")
            return
        await self.pool.execute(
            """
            INSERT INTO tag_aliases (guild_id, owner, name, alias)
            VALUES (?, ?, ?, ?)
            """,
            ctx.guild.id,
            ctx.author.id,
            name,
            alias
        )
        await ctx.reply(f"Successfully created tag alias `{alias}` for `{name}`")

    @tag_group.command(name='info')
    async def tag_info(self, ctx: FurinaCtx, *, name: str) -> None:
        """Get info of a tag by name

        Parameters
        ----------
        name : str
            Name of the tag
        """
        name = name.lower().replace('"', '').replace("'", "")
        fetched = await self.pool.fetchone(
            """
                SELECT t.name, t.content, t.owner FROM tags t WHERE t.name = ? and t.guild_id = ?
                UNION
                SELECT t.name, t.content, ta.owner FROM tags t
                JOIN tag_aliases ta ON t.guild_id = ta.guild_id and t.name = ta.name
                WHERE t.guild_id = ? AND (t.name = ? OR ta.alias = ?)
            """,
            name,
            ctx.guild.id,
            ctx.guild.id,
            name,
            name
        )
        if fetched is None:
            await ctx.send(f"No tags found for query: `{name}`")
            return
        embed = self.bot.embed
        owner = self.bot.get_user(fetched['owner'])
        embed.description = ">>> " + fetched['content'][:100]
        if len(fetched['content']) > 100:
            embed.description += "..."
        embed.add_field(name="Name", value=f"`{fetched['name']}`")
        embed.add_field(name="Owner", value=owner.mention)
        embed.set_thumbnail(url=owner.display_avatar.url)
        await ctx.reply(embed=embed)

    @tag_group.command(name='list')
    async def tag_list_slash(self, ctx: FurinaCtx) -> None:
        """List all tags in the server"""
        return await self.__tag_list(ctx)

    @commands.command(name='tags')
    async def tag_list_prefix(self, ctx: FurinaCtx) -> None:
        """List all tags in the server"""
        return await self.__tag_list(ctx)

    async def __tag_list(self, ctx: FurinaCtx) -> None:
        """List all tags in the server"""
        tags = await self.pool.fetchall(
            """
            SELECT name FROM tags
            WHERE guild_id = ?
            """,
            ctx.guild.id
        )
        if not tags:
            await ctx.reply("This server has no tags")
            return
        embeds = []
        for i in range(0, len(tags), 10):
            embed = self.bot.embed
            embed.title = f"Tags for server: {ctx.guild.name}"
            embed.description = "- " + '\n- '.join(tag['name'] for tag in tags[i:i + 10])
            embeds.append(embed)
        view = PaginatedView(timeout=180, embeds=embeds)
        await ctx.reply(embed=embeds[0], view=view)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Tags(bot))