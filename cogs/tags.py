from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from discord import app_commands, Interaction, Message
from discord.ext import commands

from furina import FurinaCog, FurinaCtx
from settings import DEFAULT_PREFIX


if TYPE_CHECKING:
    from furina import FurinaBot


class Tags(FurinaCog):
    """Tags Related Commands"""
    async def cog_load(self):
        await self.bot.pool.execute(
        """
            CREATE TABLE IF NOT EXISTS tags
            (
                guild_id BIGINT NOT NULL,
                owner BIGINT NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (guild_id, owner, name)
            );
            CREATE TABLE IF NOT EXISTS tag_aliases -- for tag aliases and look up table
            (
                guild_id BIGINT NOT NULL,
                owner BIGINT NOT NULL, -- owner of the alias, not the tag owner
                name TEXT NOT NULL,
                alias TEXT NOT NULL,
                PRIMARY KEY (guild_id, owner, name, alias)
            )
        """
        )
        return await super().cog_load()
    
    @commands.hybrid_group(name='tag', fallback='get', description="Get a tag from a query")
    async def tag_group(self, ctx: FurinaCtx, *, name: str):
        tag_content = await self.bot.pool.fetchval(
        """
            SELECT t.content FROM tags t WHERE t.name = $1 and t.guild_id = $2
            UNION 
            SELECT t.content FROM tags t 
            JOIN tag_aliases ta ON t.guild_id = ta.guild_id and t.name = ta.name
            WHERE t.guild_id = $2 AND (t.name = $1 OR ta.alias = $1)
        """, name, ctx.guild.id)
        if not tag_content:
            await ctx.send(f"No tags found for query: `{name}`")
        else:
            await ctx.send(tag_content)


    @tag_group.command(name='create', description="Create a tag")
    async def tag_create(self, ctx: FurinaCtx, name: str = None, *, content: str = None):
        def check(m: Message):
            return (m.author == ctx.author and 
                    m.channel == ctx.channel and 
                    m.content != "" and 
                    not m.content.startswith((self.bot.prefixes.get(ctx.guild.id) or DEFAULT_PREFIX, self.bot.user.mention)))
        # tag create /BLANK/
        if not name:
            try:
                await ctx.send("What is the name of the tag\n-# Type 'cancel' to cancel tag creation")
                name_input: Message = await self.bot.wait_for("message", check=check, timeout=30)
                name = name_input.content
            except asyncio.TimeoutError:
                await ctx.reply("No user input, cancelling tag creation")
        name = name.lower().replace('"', '').replace("'", "")
        if name == 'cancel':
            return await ctx.send("Cancelling tag creation")
        # tag create <name> /BLANK/
        if name and not content:
            try:
                await ctx.send("What is the content of the tag?")
                content_input: Message = await self.bot.wait_for("message", check=check, timeout=120)
                content = content_input.content
            except asyncio.TimeoutError:
                await ctx.reply("No user input, cancelling tag creation")
        if content.lower() == 'cancel':
            return await ctx.send("Cancelling tag creation")
        # tag create <name> <content>
        if not self.__name_check(ctx, name):
            return await ctx.send("Invalid tag name")
        check_exist = await self.__check_tag_name(ctx, name)
        if check_exist:
            return await ctx.send(f"Tag `{name}` already exists")
        await self.bot.pool.execute(
            """
                INSERT INTO tags (guild_id, owner, name, content)
                VALUES ($1, $2, $3, $4)
            """, ctx.guild.id, ctx.author.id, name, content)
        await ctx.send(f"Created tag `{name}`")

    def __name_check(self, ctx: FurinaCtx, name: str) -> bool:
        return not name.lower().startswith((self.bot.prefixes.get(ctx.guild.id) or DEFAULT_PREFIX, self.bot.user.mention))
    
    async def __check_tag_name(self, ctx: FurinaCtx, name: str) -> bool:
        fetched = await self.bot.pool.fetchrow(
            """
                SELECT t.content FROM tags t WHERE t.name = $1 and t.guild_id = $2
                UNION 
                SELECT t.content FROM tags t 
                JOIN tag_aliases ta ON t.guild_id = ta.guild_id and t.name = ta.name
                WHERE t.guild_id = $2 AND (t.name = $1 OR ta.alias = $1)
            """, name, ctx.guild.id)
        if fetched is not None:
            return True
        return False

    @tag_group.command(name='delete', aliases= ['del'], description="Delete a tag")
    async def tag_delete(self, ctx: FurinaCtx, *, name: str):
        name = name.lower().replace('"', '').replace("'", "")
        if ctx.author.guild_permissions.manage_guild:
            result = await self.__force_delete_tag(guild_id=ctx.guild.id, name=name)
        else:
            result = await self.__delete_tag(guild_id=ctx.guild.id, owner=ctx.author.id, name=name)
        await ctx.send(result)

    async def __force_delete_tag(self, *, guild_id: int, name: str) -> str:
        deleted = await self.bot.pool.fetchrow(
            """
                DELETE FROM tags
                WHERE guild_id = $1 AND name = $2
                RETURNING *
            """, guild_id, name)
        if deleted is None:
            return f"Tag `{name}` not found!"
        await self.bot.pool.execute(
            """
                DELETE FROM tag_aliases
                WHERE guild_id = $1 AND name = $2
            """, guild_id, name)
        return f"Deleted tag `{name}`!"
         
    async def __delete_tag(self, *, guild_id: int, owner: int, name: str) -> str:
        tag_owner: int = await self.bot.pool.fetchval("""
            SELECT owner FROM tags
            WHERE guild_id = $1 AND name = $2
            """, guild_id, name)
        if tag_owner != owner:
            return "You do not own this tag!"
        return await self.__force_delete_tag(guild_id=guild_id, name=name)
        
    @tag_group.command(name='alias', description="Create a tag alias")
    async def tag_alias(self, ctx: FurinaCtx, alias: str, *, name: str):
        check_alias_exist = await self.__check_tag_name(ctx, alias)
        if check_alias_exist:
            return await ctx.send(f"Tag `{alias}` already exists")
        check_name_exist = await self.__check_tag_name(ctx, name)
        if not check_name_exist:
            return await ctx.send(f"Cannot create alias for non-existent tag `{name}`")
        await self.bot.pool.execute(
            """
                INSERT INTO tag_aliases (guild_id, owner, name, alias)
                VALUES ($1, $2, $3, $4)
            """, ctx.guild.id, ctx.author.id, name, alias)
        await ctx.reply(f"Successfully created tag alias `{alias}` for `{name}`")

    @tag_group.command(name='info', description="Get info of a tag")
    async def tag_info(self, ctx: FurinaCtx, *, name: str):
        name = name.lower().replace('"', '').replace("'", "")
        fetched = await self.bot.pool.fetchrow(
        """
            SELECT t.name, t.content, t.owner FROM tags t WHERE t.name = $1 and t.guild_id = $2
            UNION 
            SELECT t.name, t.content, t.owner FROM tags t 
            JOIN tag_aliases ta ON t.guild_id = ta.guild_id and t.name = ta.name
            WHERE t.guild_id = $2 AND (t.name = $1 OR ta.alias = $1)
        """, name, ctx.guild.id)
        if fetched is None:
            return await ctx.send(f"No tags found for query: `{name}`")
        embed = self.bot.embed
        owner = self.bot.get_user(fetched['owner'])
        embed.description = ">>> " + fetched['content'][:100]
        if len(fetched['content']) > 100:
            embed.description += "..."
        embed.add_field(name="Name", value=f"`{fetched['name']}`")
        embed.add_field(name="Owner", value=owner.mention)
        embed.set_thumbnail(url=owner.display_avatar.url)
        await ctx.reply(embed=embed)
        


async def setup(bot: FurinaBot):
    await bot.add_cog(Tags(bot))