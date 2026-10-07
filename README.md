# catppuccin-ida

My Custom Catppuccin Theme for IDA, matching
[my Nvim syntax coloring scheme](https://github.com/Pistonite/shaft/blob/main/packages/registry/src/packages/nvim/config/lua/config/theme.lua).

- Applies basic coloring using CSS.
- Hooks into the decompiler highlighting to override stuff,
  because the default highlighting shares tags for things like keywords
  and numbers, which I need them to be different colors.
- Applies other things through Windows/QT so the UI looks more correct.

Quality: Slop + Script. I made the repo structure and AI did the research and implementation :).
Scripts have been converted to non slop;

## Requirements

IDA 9.x with IDAPython

## Installation

To install the out-of-box plugin package with prebuilt icons and predefined colors:
- Download from GitHub release and extract the archive.
- Copy `plugins/catppuccin.py` to the plugins directory (`%APPDATA\Hex-Rays\IDA Pro\plugins`).
- Copy `themes/catppuccin/` to the themes directory (`%APPDATA\Hex-Rays\IDA Pro\themes`).
- Select `Options` > `Colors...` and change the theme to `catppuccin`.
- Restart IDA so the plugin loads, to patch more colors in the UI.

If you want to customize, you have to clone the repo, change the config,
and build the plugin yourself.

## Development
Requires:
- [UV](https://docs.astral.sh/uv/)
  - To work without UV, Create a python virtual environment at `.venv`,
    then install the necessary dependencies as specified in `pyproject.toml`.
- [PNPM](https://pnpm.io/) for getting `@vscode/codicons` for icons.

The `x.ps1` (`x` for unix) is the development workflow runner.
Run scripts like `./x <script> <args> ... <script> ...`.

Setup:
```shell
./x setup
./x setup-ida   # Link IDA Installation so python imports in IDE resolves
```

The scripts find IDA by themselves: the install directory IDA records in
`%APPDATA%\Hex-Rays\IDA Pro\ida-config.json`, or else the newest
`C:\Program Files\IDA Professional ...`. If neither is there, they ask for it
once and remember the answer in `.cache/IDA_LOCATION.txt`.

Build:
```shell
./x build        # Everything below, plus the checks (check-css)

# Or one step at a time:
./x build-css    # The theme.css
./x build-icons  # The SVG icons
./x build-py     # The python plugin
```

Install - This copies the files to `%APPDATA%\Hex-Rays\IDA Pro`. Pass
in a directory if you want it installed somewhere else.
```shell
./x install
```

## Customization

To customize the colors and icons, look at `config.yaml` and `config-icons-ida.yaml`.
After editing, run the build and install.
