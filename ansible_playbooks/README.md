# Ansible Playbooks

These files were written for **Ansible v2.9**

_Tech Stack:_ Docker, Shell Scripts, Python, YAML, Ansible

_pip packages last used:_

   ```yaml
   - ansible==2.9.15    # https://pypi.org/project/ansible/2.9.15
   - jmespath           # for 'json_query' filter
   - pytz
   - colorlog           # https://pypi.org/project/colorlog
   ```

## Linting & Formatting

Here are the steps to setup a dev environment for Ansible files using VS Code (and Dev Containers extension)

1. Add these lines to _pip-requirements.txt:_

   ```txt
   ansible>=2.9,<2.10
   ansible-lint>=5.0.0,<6.0.0
   ```

2. Add these lines to _.devcontainer/devcontainer.json:_

   ```json
   {
      "customizations": {
         "vscode": {
            "extensions": [
               "redhat.vscode-yaml",
               "redhat.ansible"
            ]
         }
      }
   }
   ```

3. Add these lines to _.vscode/settings.json:_

   <sup>Most notable are "files.associations" and "editor.defaultFormatter"</sup>

   ```json
   {
      "files.associations": {
         "ansible_playbooks/**/*.yml": "ansible",
         "*plays.yml": "ansible",
         "*init.yml": "yaml",
      },
      "[yaml]": {
         "editor.defaultFormatter": "redhat.vscode-yaml"
      },
      "yaml.format.printWidth": 160,
      "yaml.format.singleQuote": true,
      "yaml.format.bracketSpacing": true,
      "yaml.format.proseWrap": "preserve",
      "yaml.schemas": {
         "https://raw.githubusercontent.com/ansible-community/schemas/main/f/ansible.json": [
            "ansible_playbooks/**/*.yml",
         ]
      },
      "ansible.validation.enabled": true,
      "ansible.python.interpreterPath": "/usr/local/bin/python",
      "ansible.ansible.useFullyQualifiedCollectionNames": true,
   }
   ```
