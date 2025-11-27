# FurinaBot

## What is this?

FurinaBot (or Furina) is a Discord bot featuring many minigames and utility features.

## Features

<details>
  <summary>Fun commands</summary>

- 8ball

- Dice roll, coin flip

- Fortune draw

</details>

<details>
  <summary>Utils commands</summary>

- Member info look up

- Bot info

- Custom Prefix

- Usage stats

</details>

</details>

<details>
  <summary>Minigame commands</summary>

- Wordle

- Letterle

- Minigame stats

</details>

And more...

## Self host

If you don't want to use my instance of the bot, you can host your own instance. Here is the step by step instruction:

> Requires Python 3.10+ (preferably newest stable)

1. Clone the repository:

    ```bash
    git clone https://github.com/thqnhz/FurinaBot.git
    cd FurinaBot
    ```

2. Install dependencies

    > Venv is recommended!
    >
    > I use `pyproject.toml` instead of `requirements.txt`, so it is pretty straight forward

    ```bash
    # using python
    python -m pip install .
    # using uv
    uv pip install .
    ```

3. Configure the bot:

    - Create a `.env` file to store your secrets

    ```env
    BOT_TOKEN=...
    WORDNIK_API=...
    ```

    > These are the 2 minimum that you would need for the bot to work

    - Edit `core/settings.py` for your likings

4. Run the bot:

    ```bash
    # using python
    python -m main.py
    # using uv
    uv run main.py
    ```

## Usage

- [Invite link](https://discord.com/oauth2/authorize?client_id=1131530915223441468&permissions=563229129829440&integration_type=0&scope=bot)
- Use the configured prefix followed by a command (e.g., `!help` for a list of commands).

## Contributing

Contributions are welcome! Please feel free to open issues or submit a pull request.

## License

This project is licensed under the `Apache version 2.0`, see `LICENSE` file for details.

## Terms of Service and Privacy Policy

Discord requires this to get the bot verified. So I'll just make this as easy to understand as possible

### Terms of service

- There isn't one.

### Privacy Policy

- The bot won't ask for your personal information whatsoever.

- It will only store either users' discord ID or what the user want it to store (using tag command).

- DM to the bot will be forwarded using discord forward feature tho. So about that.

## Disclaimer

**FurinaBot is NOT affiliated with miHoYo/HOYOVERSE in any ways.** The miHoYo related commands is using 3rd party API from <https://enka.network>
