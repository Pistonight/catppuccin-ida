# catppuccin-ida

My Custom Catppuccin Theme for IDA, matching
[my Nvim syntax coloring scheme](https://github.com/Pistonite/shaft/blob/main/packages/registry/src/packages/nvim/config/lua/config/theme.lua).

- Applies basic coloring using CSS.
- Hooks into the decompiler highlighting to override stuff,
  because the default highlighting shares tags for things like keywords
  and numbers, which I need them to be different colors.
- Applies other things through Windows/QT so the UI looks more correct.

Quality: Slop. I made the repo structure and AI did the research and implementation :)

## Requirements

IDA 9.x

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
- [Task](https://taskfile.dev/) - Optional
- [PNPM](https://pnpm.io/) for getting `@vscode/codicons` for icons.

Setup:
```shell
# With task
task setup

# Or run these:
pnpm i
uv sync
./x link-ida
```

The `link-ida` script finds the IDA installation in the default location `C:\Program Files\IDA Professional ...`.
You can pass it an installation direction if your installation is somewhere else.

Build:
```shell
# With task
task build

# Or run these:  # You could only (re)-build the parts you changed
./x build-css    # The theme.css
./x build-icons  # The SVG icons
./x build        # The python plugin
```

Install - This copies the files to `%APPDATA%\Hex-Rays\IDA Pro`. Pass
in a directory if you want it installed somewhere else.
```shell
./x install
```

## Customization

To customize the colors and icons, look at `config.yaml` and `config-icons-ida.yaml`.
After editing, run the build and install.
