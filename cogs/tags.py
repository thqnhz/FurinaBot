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
import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

import asqlite
import discord
from discord import app_commands, ui
from discord.ext import commands

from core import FurinaCog, FurinaCtx, utils
from core.sql import TagSQL
from core.views import Container, LayoutView, PaginatedView

if TYPE_CHECKING:
    import sqlite3

    from discord import Interaction, Message

    from core import FurinaBot


class TagEntry:
    """Represent a tag"""

    def __init__(self, data: sqlite3.Row) -> None:
        self.guild_id: int = data["guild_id"]
        self.owner: int = data["owner"]
        self.name: str = data["name"]
        self.content: str = data["content"]
        self.content_preview: str = ">>> " + self.content[:100]
        if len(self.content) > 100:
            self.content_preview += "..."
        self._raw_created_at: str = data["created_at"]
        self.created_at: str = utils.format_dt(
            datetime.datetime.strptime(
                self._raw_created_at, r"%Y-%m-%d %H:%M:%S.%f%z"
            )
        )
        self.uses: int = data["uses"]


class TagCreateLayoutView(LayoutView):
    """Layout view for creating a tag"""

    def __init__(
        self, *, name: str | None = None, content: str | None = None, cog: Tags
    ) -> None:
        self.name = name
        self.content = content
        self._cog = cog
        super().__init__(self.container, timeout=180)

    @property
    def container(self) -> Container:
        return Container(
            self.name_textdisplay,
            ui.Separator(),
            self.content_textdisplay,
            TagCreateActionRow(
                name=self.name, content=self.content, cog=self._cog
            ),
        )

    @property
    def name_textdisplay(self) -> ui.TextDisplay:
        return ui.TextDisplay(self.name or "*<!> Name not set <!>*")

    @property
    def content_textdisplay(self) -> ui.TextDisplay:
        return ui.TextDisplay(self.content or "*<!> Content not set <!>*")

    async def insert_tag(self, *, guild_id: int, owner: int) -> None:
        assert self.name is not None
        assert self.content is not None
        await self._cog.__insert_tag(
            guild_id=guild_id, owner=owner, name=self.name, content=self.content
        )


class TagCreateActionRow(ui.ActionRow):
    def __init__(
        self, *, name: str | None = None, content: str | None = None, cog: Tags
    ) -> None:
        super().__init__()
        self.name = name
        self.content = content
        self.message: Message | None
        self.cog = cog

    @ui.button(label="Edit", emoji="\U0000270f\U0000fe0f")
    async def edit_button(
        self, interaction: Interaction, button: ui.Button
    ) -> None:
        assert self.view is not None
        modal = TagCreateModal(
            name=self.name, content=self.content, cog=self.cog
        )
        await interaction.response.send_modal(modal)
        await modal.wait()
        self.view.message = None

    @ui.button(label="Create", emoji="\U00002705")
    async def create_button(
        self, interaction: Interaction, button: ui.Button
    ) -> None:
        assert self.view is not None
        view: TagCreateLayoutView = self.view
        if not view.name or not view.content:
            await interaction.response.send(
                "Name or content cannot be empty!", ephemeral=True
            )
        elif view.name and view.content:
            assert interaction.guild_id is not None
            await view.insert_tag(
                guild_id=interaction.guild_id, owner=interaction.user.id
            )
            await interaction.response.send(
                f"Created tag `{view.name}`", ephemeral=True
            )
            await interaction.delete_original_response()


class TagCreateModal(ui.Modal, title="Create A Tag"):
    """Modal for creating a tag"""

    def __init__(
        self, *, name: str | None = None, content: str | None = None, cog: Tags
    ) -> None:
        super().__init__()
        if name:
            self.name.required = False
            self._name = name
        if content:
            self.content.required = False
            self._content = content
        self.cog = cog

    name = ui.TextInput(
        label="Name", placeholder="Name of the tag", max_length=100
    )
    content = ui.TextInput(
        label="Content",
        placeholder="Content of the tag",
        style=discord.TextStyle.long,
        max_length=1000,
    )

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.edit_message(
            view=TagCreateLayoutView(
                name=self.name.value or self._name,
                content=self.content.value or self._content,
                cog=self.cog
            )
        )


class Tags(FurinaCog):
    """Tags Related Commands"""

    @property
    def emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str("\U0001f3f7\U0000fe0f")

    async def cog_load(self) -> None:
        self.pool: TagSQL = TagSQL(
            await asqlite.create_pool(str(Path() / "db" / "tags.db"))
        )
        await self.pool.create_tables()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        await self.pool.pool.close()

    async def __get_tag_content(
        self, *, guild_id: int, name: str
    ) -> str | None:
        """Get tag content from database

        Parameters
        ----------
        guild_id : int
            Guild ID that is fetching the tag.
        name : str
            Name of the tag to fetch

        Returns
        -------
        str, optional
            Tag content if it exists, else `None`
        """
        return await self.pool.fetchval(
            """
            SELECT T.content FROM tags T
            LEFT JOIN tag_aliases TA
            ON T.guild_id = TA.guild_id AND T.name = TA.name
            WHERE T.guild_id = ? AND (T.name = ? OR TA.alias = ?)
            """,
            guild_id,
            name,
            name,
        )

    async def __get_user_input(
        self, ctx: FurinaCtx, *, prompt: str
    ) -> str | None:
        """Get user input for tag creation"""

        # Small check function for input checking
        def check(m: Message) -> bool:
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and len(m.content) > 0
                and not m.content.startswith(
                    tuple(self.bot.get_pre(self.bot, m))
                )
            )

        try:
            await ctx.send(prompt)
            msg = await self.bot.wait_for("message", check=check, timeout=180)
            if msg.content.lower() == "cancel":
                await ctx.send("Tag creation cancelled")
                return None
            return msg.content.strip("'\" ")
        except asyncio.TimeoutError:
            await ctx.send("No user input, cancelling tag creation")
            return None

    async def __check_tag_name(self, guild_id: int, *, name: str) -> bool:
        """Check if a tag already exists

        Parameters
        ----------
        guild_id : int
            Guild id where the tag belong
        name : str
            Name of the tag to check

        Returns
        -------
        bool
            Whether the tag exists or not
        """
        # list of reserved tag names
        reserved = [
            command.name
            for command in self.walk_commands()
            if command.qualified_name.startswith("tag")
        ]
        # True if tag name starts with reserved names
        if name.startswith(tuple(reserved)):
            return True
        # None -> Tag does not exist
        fetched = await self.__get_tag_content(guild_id=guild_id, name=name)
        in_fetched = fetched is not None
        return bool(in_fetched)

    async def __handle_tag_creation_prefix(
        self,
        ctx: FurinaCtx,
        *,
        name: str | None = None,
        content: str | None = None,
    ) -> None:
        """|coro|
        Handle tag creation when invoked with prefix

        Parameters
        ----------
        ctx : FurinaCtx
            Invoked context
        name : str, optional
            Name of the tag
        content : str, optional
            Content of the tag
        """
        # tag create /BLANK/
        if not name:
            name = await self.__get_user_input(
                ctx, prompt="What is the name of the tag?"
            )
            if not name:
                return
        if await self.__check_tag_name(ctx.guild.id, name=name):
            await ctx.send(
                f"Tag `{name}` already exists or in reserved names list"
            )
            return
        # tag create <name> /BLANK/
        if not content:
            content = await self.__get_user_input(
                ctx, prompt="What is the content of the tag?"
            )
            if not content:
                return
        # tag create <name> <content>
        await self.__insert_tag(
            guild_id=ctx.guild.id,
            owner=ctx.author.id,
            name=name,
            content=content,
        )
        await ctx.send(f"Created tag `{name}`")

    async def __handle_tag_creation_slash(
        self,
        interaction: Interaction,
        *,
        name: str | None = None,
        content: str | None = None,
    ) -> None:
        """|coro|
        Handle tag creation when invoked with slash

        Parameters
        ----------
        interaction : Interaction
            Invoked interaction
        name : str, optional
            Name of the tag
        content : str, optional
            Content of the tag
        """
        await interaction.response.defer(ephemeral=True)
        assert interaction.guild_id is not None
        if (
            name
            and content
            and not await self.__check_tag_name(interaction.guild_id, name=name)
        ):
            await self.__insert_tag(
                guild_id=interaction.guild_id,
                owner=interaction.user.id,
                name=name,
                content=content,
            )
            return
        view = TagCreateLayoutView(name=name, content=content, cog=self)
        view.message = await interaction.followup.send(view=view)

    async def __insert_tag(
        self, *, guild_id: int, owner: int, name: str, content: str
    ) -> None:
        """|coro|
        Insert a tag into the database

        Parameters
        ----------
        guild_id : int
            Guild ID
        owner : int
            ID of the owner of the tag
        name : str
            Name of the tag
        content : str
            Content of the tag
        """
        await self.pool.execute(
            """
            INSERT INTO tags (guild_id, owner, name, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            guild_id,
            owner,
            name,
            content,
            str(utils.utcnow()),
        )

    @commands.hybrid_group(name="tag", fallback="get")
    async def tag_group(self, ctx: FurinaCtx, *, name: str) -> None:
        """Get a tag by name

        What is tag?
        Tag is a silly text that is **user** created.
        It may or may not be useful.
        You can create your own tag with `tag create` command.

        Parameters
        ----------
        name : str
            Name of the tag
        """
        tag_content = await self.__get_tag_content(
            guild_id=ctx.guild.id, name=name.lower()
        )
        if not tag_content:
            await ctx.send(f"No tags found for query: `{name}`")
        else:
            await self.pool.execute(
                """
                UPDATE tags
                SET uses = uses + 1
                WHERE guild_id = ? AND name = ?
                """,
                ctx.guild.id,
                name,
            )
            await ctx.send(tag_content)

    @tag_group.autocomplete("name")
    async def tag_name_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice]:
        rows = await self.pool.fetchall(
            """
            SELECT T.name FROM tags T
            LEFT JOIN tag_aliases TA
                ON T.guild_id = TA.guild_id
                AND T.name = TA.name
            WHERE T.guild_id = ?
                AND (
                    instr(T.name, ?) > 0 OR instr(TA.alias, ?)
                )
            LIMIT 25
            """,
            interaction.guild_id,
            current,
            current,
        )
        return [
            app_commands.Choice(name=row["name"], value=row["name"])
                for row in rows
        ]

    @tag_group.command(name="create")
    async def tag_create_command(
        self,
        ctx: FurinaCtx,
        name: str | None = None,
        *,
        content: str | None = None,
    ) -> None:
        """Create a tag

        Tag name/content cannot contain the bot's prefix or mention.
        To make a name that contains spaces, wrap it in quotes.
        Can be create "interactively" when not specify the content. Or neither.
        Alternatively, use the slash version of this command.

        Parameters
        ----------
        name : str, optional
            Name of the tag
        content : str, optional
            Content of the tag
        """
        if not ctx.interaction:
            await self.__handle_tag_creation_prefix(
                ctx, name=name, content=content
            )
        else:
            ctx: Interaction = cast("Interaction", ctx)
            await self.__handle_tag_creation_slash(
                ctx, name=name, content=content
            )

    @tag_group.command(name="edit")
    async def tag_edit_command(
        self, ctx: FurinaCtx, name: str, *, content: str
    ) -> None:
        """Edit your tag

        You can only edit your own tag.
        If you edit the tag that originally is an alias of another tag,
        it will become a new tag.

        Parameters
        ----------
        name : str
            The name of the tag you want to edit
        content : str
            The new content of the tag
        """
        tag_owner = await self.pool.fetchval(
            """
            SELECT owner FROM tags
            WHERE guild_id = ? AND name = ? AND owner = ?
            """,
            ctx.guild.id,
            name,
            ctx.author.id,
        )
        if tag_owner is not None:
            await self.pool.execute(
                """
                UPDATE tags
                SET content = ?
                WHERE guild_id = ? AND name = ?
                """,
                content,
                ctx.guild.id,
                name,
            )
            await ctx.reply(f"Updated tag `{name}`")
            return
        tag_alias_owner = await self.pool.fetchval(
            """
            SELECT owner
            FROM tag_aliases
            WHERE guild_id = ? AND alias = ? AND owner = ?
            """,
            ctx.guild.id,
            name,
            ctx.author.id,
        )
        if tag_alias_owner is not None:
            await self.pool.execute(
                """
                DELETE FROM tag_aliases
                WHERE guild_id = ? AND alias = ?
                """,
                ctx.guild.id,
                name,
            )
            await self.__insert_tag(
                guild_id=ctx.guild.id,
                owner=ctx.author.id,
                name=name,
                content=content
            )
            await ctx.reply(f"Updated tag `{name}`")
            return
        await ctx.reply("Failed to edit the tag, is the tag even exist?")

    @tag_edit_command.autocomplete(name="name")
    async def owned_tag_name_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice]:
        rows = await self.pool.fetchall(
            """
            SELECT T.name FROM tags T
            LEFT JOIN tag_aliases TA
                ON T.guild_id = TA.guild_id
                AND T.name = TA.name
            WHERE T.guild_id = ?
                AND T.owner = ?
                AND (
                    instr(T.name, ?) > 0 OR instr(TA.alias, ?)
                )
            LIMIT 25
            """,
            interaction.guild_id,
            interaction.user.id,
            current,
            current,
        )
        return [
            app_commands.Choice(name=row["name"], value=row["name"])
                for row in rows
        ]

    @tag_group.command(name="delete", aliases=["del"])
    async def tag_delete(self, ctx: FurinaCtx, *, name: str) -> None:
        """Delete a tag by name

        Delete a tag with provided name.
        You can only delete your own tag.
        However if you have `Manage Server` permission,
        you can force delete a tag.

        Parameters
        ----------
        name : str
            Name of the tag
        """
        name = name.lower().replace('"', "").replace("'", "")
        if ctx.author.guild_permissions.manage_guild:
            result = await self.__force_delete_tag(
                guild_id=ctx.guild.id, name=name
            )
        else:
            result = await self.__delete_tag(
                guild_id=ctx.guild.id, owner=ctx.author.id, name=name
            )
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
            name,
        )
        if deleted is None:
            deleted = await self.pool.fetchone(
                """
                DELETE FROM tag_aliases
                WHERE guild_id = ? AND alias = ?
                """,
                guild_id,
                name,
            )
        else:
            await self.pool.execute(
                """
                DELETE FROM tag_aliases
                WHERE guild_id = ? AND name = ?
                """,
                guild_id,
                name,
            )
        if deleted is None:
            return f"No tags or aliases with query `{name}` for deletion"
        return f"Deleted tag `{name}`!"

    async def __delete_tag(
        self, *, guild_id: int, owner: int, name: str
    ) -> str:
        """Check if the user is the owner of the tag and force delete it"""
        tag_owner = await self.pool.fetchval(
            """
            SELECT owner FROM tags
            WHERE guild_id = ? AND name = ?
            """,
            guild_id,
            name,
        )
        if tag_owner != owner:
            return "You do not own this tag!"
        return await self.__force_delete_tag(guild_id=guild_id, name=name)

    @tag_group.command(name="alias")
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
        check_alias_exist = await self.__check_tag_name(
            ctx.guild.id, name=alias
        )
        if check_alias_exist:
            await ctx.send(f"Tag `{alias}` already exists")
            return
        check_name_exist = await self.__check_tag_name(ctx.guild.id, name=name)
        if not check_name_exist:
            await ctx.send(f"Cannot create alias for non-existent tag `{name}`")
            return
        await self.pool.execute(
            """
            INSERT INTO tag_aliases (guild_id, owner, name, alias, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ctx.guild.id,
            ctx.author.id,
            name,
            alias,
            str(utils.utcnow()),
        )
        await ctx.reply(
            f"Successfully created tag alias `{alias}` for `{name}`"
        )

    @tag_group.command(name="info")
    async def tag_info(self, ctx: FurinaCtx, *, name: str) -> None:
        """Get info of a tag by name

        Parameters
        ----------
        name : str
            Name of the tag
        """
        name = name.strip("'\"")
        fetched = await self.pool.fetchone(
            """
            SELECT t.guild_id, t.name, t.content, t.owner, t.created_at, t.uses
            FROM tags t
            WHERE t.name = ? and t.guild_id = ?
            UNION
            SELECT
            ta.guild_id, ta.name, t.content, ta.owner, ta.created_at, ta.uses
            FROM tags t
            JOIN tag_aliases ta
            ON t.guild_id = ta.guild_id and t.name = ta.name
            WHERE t.guild_id = ? AND (t.name = ? OR ta.alias = ?)
            """,
            name,
            ctx.guild.id,
            ctx.guild.id,
            name,
            name,
        )
        if fetched is None:
            await ctx.send(f"No tags found for query: `{name}`")
            return
        embed = self.bot.embed
        tag = TagEntry(fetched)
        owner = self.bot.get_user(tag.owner)
        embed.description = tag.content_preview
        embed.add_field(name="Name", value=f"`{tag.name}`")
        if owner:
            embed.set_thumbnail(url=owner.display_avatar.url)
            embed.add_field(name="Owner", value=owner.mention)
        else:
            embed.add_field(name="Owner", value="Owner left the server")
        embed.add_field(name="Created at", value=tag.created_at)
        embed.add_field(name="Uses", value=tag.uses)

        await ctx.reply(embed=embed)

    @tag_group.command(name="list")
    async def tag_list_slash(self, ctx: FurinaCtx) -> None:
        """List all tags in the server"""
        return await self.__tag_list(ctx)

    @commands.command(name="tags")
    async def tag_list_prefix(self, ctx: FurinaCtx) -> None:
        """List all tags in the server"""
        return await self.__tag_list(ctx)

    async def __tag_list(self, ctx: FurinaCtx) -> None:
        """List all tags in the server"""
        tags = await self.pool.fetchall(
            """
            SELECT name
            FROM tags
            WHERE guild_id = ?
            """,
            ctx.guild.id,
        )
        if not tags:
            await ctx.reply("This server has no tags")
            return
        embeds = []
        for i in range(0, len(tags), 10):
            embed = self.bot.embed
            embed.title = f"Tags for server: {ctx.guild.name}"
            embed.description = "- " + "\n- ".join(
                tag["name"] for tag in tags[i : i + 10]
            )
            embeds.append(embed)
        view = PaginatedView(timeout=180, embeds=embeds)
        await ctx.reply(embed=embeds[0], view=view)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Tags(bot))
