from wavelink import Playable, TrackSource
from discord import Embed, Color, Member
from settings import *
from typing import Optional


class ErrorEmbed(Embed):
    """
    Embed cho Lỗi.
    
    Parameters
    -----------------
    description
        str = None
    """
    def __init__(self, description=None):
        super().__init__(color=Color.red(), title="— Lỗi", description=description)


class FooterEmbed(Embed):
    """
    Embed chứa sẵn footer.

    Parameters
    ------------------
    color
        discord.Color = None
    title
        str = None
    description
        str = None
    """
    def __init__(self, color: Color = None, title: str = None, description: str = None):
        super().__init__(title=title, description=description, color=color)
        self.set_footer(text="Coded by ThanhZ")


class LoadingEmbed(FooterEmbed):
    """
    Loading Embed

    Parameters
    -----------
    author_name
        str = 'Đang tải...'
    """
    def __init__(self, author_name: str = "Đang tải..."):
        super().__init__()
        self.set_author(name=author_name, icon_url=LOADING_GIF)


class PlayerEmbed(FooterEmbed):
    """
    Embed cập nhật mỗi khi bài hát mới được phát.
    """
    def __init__(self, track):
        super().__init__(
            title=f"Đang phát: **{track}**",
            description="Bạn có thể sử dụng các nút bên dưới để thực hiện nhanh các lệnh.",
        )
        self.url = track.uri or None
        self.set_author(name=track.author, icon_url=PLAYING_GIF)
        if hasattr(track, "thumb"):
            self.set_thumbnail(url=track.thumb)


class AvatarEmbed(FooterEmbed):
    """
    Embed có Footer và avatar người sử dụng lệnh (nếu có).
    """
    def __init__(self, title: str = None, desc: str = None, *, user: Member):
        super().__init__(title=title, description=desc)
        self.color = Color.green()
        if user.avatar is not None:
            self.set_thumbnail(url=user.avatar.url)


class ImageEmbed(FooterEmbed):
    """
    Embed có Footer và avatar người sử dụng lệnh (nếu có).
    """

    def __init__(self, title: str = None, desc: str = None, *, image: str):
        super().__init__(title=title, description=desc)
        self.color = Color.green()
        self.set_image(url=image)

