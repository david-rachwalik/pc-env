#!/usr/bin/env python
"""Command to provision VS Code"""

import argparse
from typing import List, Optional

import logging_boilerplate as log
import shell_boilerplate as sh

# -------- Provision Visual Studio Code (and extensions) --------

vscode_extensions: List[str] = [
    # --- Baseline ---
    "bierner.markdown-preview-github-styles",
    "christian-kohler.path-intellisense",
    "DavidAnson.vscode-markdownlint",
    "esbenp.prettier-vscode",
    "felipecaputo.git-project-manager",
    "mikestead.dotenv",
    "natqe.reload",
    # 'TabNine.tabnine-vscode',  # code suggestions
    "theumletteam.umlet",  # UML Diagrams
    "VisualStudioExptTeam.intellicode-api-usage-examples",
    "VisualStudioExptTeam.vscodeintellicode",
    "vscode-icons-team.vscode-icons",
    "wayou.vscode-todo-highlight",
    # --- DevOps ---
    "donjayamanne.githistory",
    "hashicorp.terraform",
    "ms-vscode.azure-account",
    "ms-azure-devops.azure-pipelines",
    "ms-vscode-remote.vscode-remote-extensionpack",  # installs others
    "ms-vscode.powershell",
    "msazurermtools.azurerm-vscode-tools",
    # --- HTML, CSS/SASS, JavaScript/TypeScript ---
    "dbaeumer.vscode-eslint",
    # 'DigitalBrainstem.javascript-ejs-support',
    "formulahendry.auto-close-tag",
    "formulahendry.auto-rename-tag",
    "rbbit.typescript-hero",
    "sibiraj-s.vscode-scss-formatter",
    "steoates.autoimport",
    "syler.sass-indented",
    "sz-p.dependencygraph",
    "WooodHead.disable-eslint-rule",
    # 'xabikos.JavaScriptSnippets',
    # --- Python ---
    "Cameron.vscode-pytest",
    # 'donjayamanne.python-environment-manager',
    "ms-python.isort",
    "ms-python.pylint",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "njpwerner.autodocstring",
    # --- Other Languages ---
    "bowlerhatllc.vscode-as3mxml",  # ActionScript
    "redhat.vscode-yaml",
    # 'rog2.luacheck',
    # 'tangzx.emmylua',
    # --- Databases ---
    "mongodb.mongodb-vscode",
    "ms-azuretools.vscode-cosmosdb",
    # --- Server - Node.js ---
    "42Crunch.vscode-openapi",
    "christian-kohler.npm-intellisense",
    "howardzuo.vscode-npm-dependency",
    # --- Server - Azure ---
    "ms-vscode.vscode-node-azure-pack",  # install others
    # 'ms-azuretools.azure-dev',
    # 'ms-azuretools.vscode-azureappservice',
    # 'ms-azuretools.vscode-azurefunctions',
    # 'ms-azuretools.vscode-azureresourcegroups',
    # 'ms-azuretools.vscode-azurestaticwebapps',
    # 'ms-azuretools.vscode-azurestorage',
    # 'ms-azuretools.vscode-azureterraform',
    # 'ms-azuretools.vscode-azurevirtualmachines',
    # --- Angular ---
    "Angular.ng-template",
    # --- Vue ---
    # 'MisterJ.vue-volar-extention-pack',  # installs others
    # 'Vue.volar',
    # 'Vue.vscode-typescript-vue-plugin',
    # 'Wscats.vue',
    # --- C# .NET ---
    "ms-dotnettools.csharp",
    "ms-dotnettools.vscode-dotnet-runtime",
]


# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------


def trim_string_list(data: Optional[List[str]] = None) -> List[str]:
    """Method that trims a list of empty string entries"""
    # https://datatofish.com/remove-empty-strings-from-list
    result = []
    if data:
        result = [x for x in data if x != ""]
    return result


def list_extensions_installed() -> List[str]:
    """Method that fetches a list of VS Code extensions installed"""
    command: List[str] = ["code", "--list-extensions"]
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    vscode_extensions_installed = str(process.stdout).splitlines()
    vscode_extensions_installed.sort()
    return vscode_extensions_installed


def list_extensions_to_install(installed: List[str]) -> List[str]:
    """Method that fetches a list of VS Code extensions to install"""
    if not installed:
        return []
    vscode_extensions_to_install = list(set(vscode_extensions).difference(installed))
    vscode_extensions_to_install.sort()
    return vscode_extensions_to_install


def list_extensions_unexpected(installed: List[str]) -> List[str]:
    """Method that fetches a list of VS Code extensions unexpectedly installed"""
    if not installed:
        return []
    vscode_extensions_unexpected = list(set(installed).difference(vscode_extensions))
    vscode_extensions_unexpected.sort()
    return vscode_extensions_unexpected


# https://code.visualstudio.com/docs/editor/extension-marketplace#_command-line-extension-management
def install_extension(extension_id: str) -> bool:
    """Method that installs a VS Code extension"""
    command: List[str] = ["code", "--install-extension", extension_id]
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# ------------------------ Main program ------------------------
# Initialize the logger
BASENAME = "provision_vscode"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: log.Logger = log.get_logger(BASENAME)

if __name__ == "__main__":

    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        return parser.parse_args()

    ARGS = parse_arguments()

    # Configure the logger
    LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("--------------------------------------------------------")

    # --- Gather extension information ---
    extensions_installed = list_extensions_installed()
    LOG.info(f"extensions installed: {extensions_installed}")
    extensions_to_install = list_extensions_to_install(extensions_installed)
    LOG.info(f"extensions to install: {extensions_to_install}")
    extensions_unexpected = list_extensions_unexpected(extensions_installed)
    LOG.info(f"extensions unexpected: {extensions_unexpected}")

    # --- Install missing extensions as needed ---
    for extension in extensions_to_install:
        LOG.debug(f'preparing to install "{extension}" extension...')
        install_extension(extension)

    # Upgrade to extensions not necessary - VS Code handles automatically

    LOG.debug("--------------------------------------------------------")
    LOG.debug("--- end point reached :3 ---")
    sh.exit_process()


# :: Usage Example ::
# setup --tags 'py' --skip-tags 'windows'
# app --debug login
# app --debug --secret-key='AutoTestKey' --secret-value='007' secret
