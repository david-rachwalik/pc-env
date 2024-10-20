#!/bin/bash

# --- Example Usage Commands ---
# setup --tags sh
# app_iterate


# --- Script to quickly iterate upon 'app' command for development ---
cd ~/pc-env/ansible_playbooks
ansible-playbook system_setup.yml --tags "py" --skip-tags "windows"

# --- Test Azure login (service principal) ---
# app login --debug

# --- Test creating a secret in Azure Key Vault ---
# app secret --debug --resource-group="Main" --key-vault="main-keyvault" --secret-key="AutoTestKey" --secret-value="007"

# --- Test creating an ASP.NET Core Application ---
# app client --debug --framework "netcoreapp3.1" --solution "Tutorials-net3-1-WebApps-RazorPages" --project "RazorPagesMovie"
# app client --debug --framework "netcoreapp3.1" --solution "Tutorials-net3-1-DataAccess-RazorPages" --project "ContosoUniversity" --strat "database"
# app client --debug --framework "net5.0" --solution "Tutorials-net5-0-WebApps-RazorPages" --project "RazorPagesMovie"
# app client --debug --framework "net5.0" --solution "Tutorials-net5-0-DataAccess-RazorPages" --project "ContosoUniversity" --strat "database"
# app client --debug --framework "net5.0" --solution "Tutorials-net5-0-WebApiApps" --project "TodoApi" --strat "api"
# app client --debug --framework "net5.0" --solution "Templates-net5-0" --project "Templates-net5-0.WebApp.Base"
# app client --debug --framework "net5.0" --solution "Templates-net5-0" --project "Templates-net5-0.WebApp.SqlDb" --strat "database"
# app client --debug --framework "net5.0" --solution "Templates-net5-0" --project "Templates-net5-0.WebApi.Base" --strat "api"

# app client --debug --framework "net6.0" --solution "Tutorials-net6-0-WebApps-RazorPages" --project "RazorPagesMovie"
# app client --debug --framework "net6.0" --solution "Tutorials-net6-0-DataAccess-RazorPages" --project "ContosoUniversity" --strat "database"
app client --debug --framework "net6.0" --solution "Templates-net6-0" --project "Templates-net6-0.WebApp.Base"
app client --debug --framework "net6.0" --solution "Templates-net6-0" --project "Templates-net6-0.WebApp.SqlDb" --strat "database"
# app client --debug --framework "net6.0" --solution "Templates-net6-0" --project "Templates-net6-0.WebApp.Identity" --strat "identity"
# app client --debug --framework "net6.0" --solution "Templates-net6-0" --project "Templates-net6-0.WebApp.UnitTests" --strat "test"
# app client --debug --framework "net6.0" --solution "Templates-net6-0" --project "Templates-net6-0.WebApi.API" --strat "api"

# app client --debug --source "github" --solution "DMR" --project "DMR.WebApp" --strat "database"
# app client --debug --source "github" --solution "DMR" --project "DMR.WebApp" --strat "identity"
# app client --debug --source "tfsgit" --solution "SexBound" --project "SexBound.WebApp" --strat "identity"
# app client --debug --source "tfsgit" --solution "CorruptionOfChampions" --project "CorruptionOfChampions.Conversion" --strat "identity"
# app client --debug --source "tfsgit" --solution "CorruptionOfChampions" --project "CorruptionOfChampions.WebApp" --strat "identity"


# --- Test deploying ARM template to 'Development' environment ---
# app deploy --debug --project "ArmTemplates" --arm "linux/key_vault"
# app deploy --debug --project "ArmTemplates" --arm "linux/key_vault_secret"
# app deploy --debug --project "ArmTemplates" --arm "linux/app_service_plan"
# app deploy --debug --project "ArmTemplates" --arm "linux/app_service"
# app deploy --debug --project "ArmTemplates" --arm "linux/sql_server"
# app deploy --debug --project "ArmTemplates" --arm "linux/sql_database"
# app deploy --debug --project "ArmTemplates" --arm "linux/storage_account"

# app deploy --debug --project "ArmTemplates" --arm "linked/key_vault_secret"
# app deploy --debug --project "ArmTemplates" --arm "linked/app_service_sql"

# --- Test deploying ARM template to 'Release' environment ---
# app deploy --debug --resource-group="Main" --environment="Prod"
