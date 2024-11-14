#!/usr/bin/env python
"""Command to control application resources"""

#       *** Resources ***
# account:          Will only pair with 'login'; sign-in/config for 'az' & 'az devops'
# secret:           Key vault secrets
# deploy:           Resource manager template deployment to resource group
# pipeline:         Pipelines (var groups, connections, end-points, etc.)
#       *** Actions ***
# login:            Ensure signed-in & configured; manual login prompt first time
# set:              Create/update an Azure resource
# get:              Show status output for a resource
# remove:           Delete resources (not immediately purge, based on retention)
#       *** Options ***
# --debug:          Enable to display log messages for development
# --quiet:          Enable to reduce verbosity; will error instead of login prompt

# :-Strategies-:    login_strategy, group_strategy, service_principal_strategy, secret_strategy


#       *** Actions ***
# login:            Ensure credential file exists or prompts manual login to create
# show:             Print output for a resource, key vault secret, etc.
# register:         Register an Azure Active Directory application
# deploy:           Deploy an application to Azure (webapp, api, nuget package)
# status:           View running state of deployed application


# :: Usage Example ::
# setup --tags "py" --skip-tags "windows"
# app --debug login
# app --debug --secret-key="AutoTestKey" --secret-value="007" secret
# app --debug --project="test" --arm="test-deploy" deploy


import argparse
from typing import Any, Dict, List, Tuple

import azure_boilerplate as az
import azure_devops_boilerplate as az_devops
import dotnet_boilerplate as net
import git_boilerplate as git
import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Global Azure Commands ------------------------

# --- Strategies ---


def resource_group_strategy(resource_group_name: str, location: str) -> az.ResourceGroup:
    """Method to setup an Azure resource group"""
    if not ACCOUNT.isSignedIn:
        LOG.debug("account is not signed in")
        return az.ResourceGroup()
    # Ensure resource group exists
    resource_group = az.resource_group_get(resource_group_name)
    LOG.debug(f"resource_group data: {resource_group}")
    if not resource_group.isValid:
        LOG.warning("resource group is missing, creating...")
        resource_group = az.resource_group_set(resource_group_name, location)
    return resource_group


def key_vault_strategy(location: str, resource_group_name: str, key_vault_name: str) -> az.KeyVault:
    """Method to setup an Azure key vault"""
    if not ACCOUNT.isSignedIn:
        LOG.debug("account is not signed in")
        return az.KeyVault()

    # Ensure resource group exists
    resource_group = resource_group_strategy(resource_group_name, location)
    if not resource_group.isValid:
        LOG.error("failed to create resource group")
        sh.fail_process()

    # Ensure key vault exists
    key_vault = az.key_vault_get(key_vault_name, resource_group_name)
    if not key_vault.isValid:
        LOG.warning("key vault doesn't exists, creating...")
        key_vault = az.key_vault_set(key_vault_name, resource_group_name)

    LOG.debug(f"key vault data: {key_vault}")
    return key_vault


def ad_group_strategy(ad_member_id: str, ad_group_name: str = "main-ad-group") -> az.AdGroup:
    """Method to setup an Azure Active Directory group"""
    ad_group = az.AdGroup()
    if not ACCOUNT.isSignedIn:
        LOG.debug("account is not signed in")
        return ad_group

    # Ensure active directory group exists
    ad_group = az.ad_group_get(ad_group_name)
    LOG.debug(f"ad_group: {ad_group}")
    if not ad_group.isValid:
        LOG.warning("active directory group is missing, creating...")
        ad_group = az.ad_group_set(ad_group_name)

    # Ensure id is member of active directory group
    is_ad_group_member: bool = az.ad_group_member_get(ad_group_name, ad_member_id)
    if not is_ad_group_member:
        LOG.warning("active directory group member is missing, adding...")
        is_ad_group_member = az.ad_group_member_set(ad_group_name, ad_member_id)

    # Ensure access role is assigned to active directory group
    scope: str = f"/subscriptions/{ACCOUNT.subscriptionId}"
    role_assigned: bool = az.role_assign_get(ad_group.id, scope)
    if not role_assigned:
        LOG.warning("role is not assigned to active directory group, adding...")
        role_assigned = az.role_assign_set(ad_group.id, scope)

    LOG.debug(f"AD group data: {ad_group}")
    return ad_group


# TODO: figure out whether still needed
def service_principal_strategy(tenant: str, service_principal_name: str, app_id: str) -> az.ServicePrincipal:
    """Method to setup an Azure service principal"""
    if not ACCOUNT.isSignedIn:
        LOG.debug("account is not signed in")
        return az.ServicePrincipal()
    # Full filepath to service principal data
    service_principal_name = az.format_resource_name(service_principal_name)
    # Ensure service principal exists
    service_principal: az.ServicePrincipal = az.service_principal_get(service_principal_name, tenant=tenant)
    if not service_principal.isValid:
        LOG.debug("service principal credentials not found, creating...")
        service_principal = az.service_principal_set(service_principal_name, app_id)
    return service_principal


# https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-local-development-service-principal
def login_service_principal_strategy() -> az.ServicePrincipal:
    """Method to sign-in an Azure service principal"""
    service_principal = az.ServicePrincipal()
    # Full filepath to service principal data
    sp_dir = ARGS.login_service_principal_dir
    sp_name = az.format_resource_name(ARGS.login_service_principal)
    service_principal_path = sh.join_path(sh.expand_path(sp_dir), f"{sp_name}.json")

    # Ensure service principal exists in Azure and local
    if sh.path_exists(service_principal_path, "f"):
        # Gather login info from service principal JSON
        LOG.info("service principal file exists, loading...")
        service_principal = az.service_principal_get(sp_name, sp_dir)
        LOG.debug(f"service principal (local) data: {service_principal}")
        return service_principal

    LOG.debug("service principal file missing, checking Azure...")
    if not ACCOUNT.isSignedIn:
        LOG.debug("account is not signed in")
        return service_principal

    # Ensure key vault exists
    key_vault = key_vault_strategy(ARGS.location, ARGS.login_resource_group, ARGS.login_key_vault)
    if not key_vault.isValid:
        LOG.error("failed to retrieve valid key vault details")
        return service_principal

    # Ensure service principal exists
    service_principal = az.service_principal_get(sp_name)
    # LOG.debug(f'service principal data: {service_principal}')

    if service_principal.isValid:
        # Check for passphrase as key vault secret (to cloud share across systems)
        key_vault_secret = az.key_vault_secret_get(ARGS.login_key_vault, sp_name)
        LOG.debug(f"key vault secret: {key_vault_secret}")
        if key_vault_secret:
            LOG.info("successfully found service principal password in key vault!")
            service_principal.password = key_vault_secret
        else:
            # Service principal in Azure but not local file, must reset pass to regain access
            LOG.info("service principal found in Azure but not local, resetting credentials...")
            service_principal_reset = az.service_principal_rbac_set(sp_name, True)
            # LOG.debug(f'service principal reset: {service_principal_reset}')
            # Grab service principal credential/password
            service_principal.password = service_principal_reset.password
            service_principal.changed = True
            # TODO: verify below is always true
            appIdMatch = service_principal.appId == service_principal_reset.appId
            LOG.info(f'service principal "appId" match: {appIdMatch}')
    else:
        key_vault_secret = ""
        LOG.warning("service principal credentials not found, creating...")
        service_principal = az.service_principal_rbac_set(sp_name)
        # LOG.debug(f'service principal data: {service_principal}')
        # Last chance to have service principal
        if not service_principal.isValid:
            LOG.error("failed to create service principal")
            return service_principal
        else:
            LOG.info("successfully created service principal!")
            # Grab service principal object id
            service_principal_new = az.service_principal_get(sp_name)
            # LOG.debug(f'service principal new: {service_principal_new}')
            service_principal.id = service_principal_new.id

    LOG.debug(f"service principal data: {service_principal}")

    # Store service principal details in JSON file
    LOG.info("saving service principal credentials to local JSON...")
    is_sp_saved = az.service_principal_save(service_principal_path, service_principal)
    if is_sp_saved:
        LOG.info("successfully saved service principal credentials to local JSON!")
    else:
        LOG.error("failed to save service principal credentials to local JSON")

    # Store credential/password (from "service_principal_rbac_set") in Azure key vault
    do_secret_save: bool = bool(service_principal.password) and bool(service_principal.password != key_vault_secret)
    # if service_principal.password and not key_vault_secret:
    if do_secret_save:
        LOG.info("service principal credential not in Azure key vault, saving...")
        secret_save_result = az.key_vault_secret_set(ARGS.login_key_vault, sp_name, service_principal.password)
        if secret_save_result:
            LOG.info("successfully saved service principal credential as Azure key vault secret")
        else:
            LOG.error("failed to store service principal credential as Azure key vault secret")

    # TODO: manage service principal security groups
    # use 'az role assignment create' on groups, not service principals
    # https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli#manage-service-principal-roles

    # Ensure active directory groups/roles exist
    if service_principal.changed:
        ad_group = ad_group_strategy(service_principal.id)
        LOG.debug(f"AD group data: {ad_group}")

    # TODO: manage service principal security access to Key Vault:
    # - manually enabled ARM for template deployment in Portal
    # - manually added the service principal as access policy in Portal
    # - examine key_vault returned from strategy

    return service_principal


def login_strategy(retry: bool = True) -> az.Account:
    """Method to sign-in an Azure account"""
    global ACCOUNT  # to assign a value to global variable within a function (not needed for attribute values)
    # Full filepath to service principal data
    sp_dir = ARGS.login_service_principal_dir
    sp_name = az.format_resource_name(ARGS.login_service_principal)
    service_principal_path = sh.join_path(sh.expand_path(sp_dir), f"{sp_name}.json")

    # Check if account subscription exists (first chance to be signed-in)
    LOG.info("checking if already signed-in Azure...")
    ACCOUNT = az.account_get(ARGS.subscription)
    # LOG.debug(f'account: {account}')

    # Ensure service principal credentials exist
    service_principal = login_service_principal_strategy()
    # LOG.debug(f'service principal data: {service_principal}')
    ACCOUNT.login_sp = service_principal

    # --- elif used to limit recursive activity ---

    if service_principal.changed:
        # Confirm updated service principal login connects
        LOG.info("detected service principal change, preparing to use new credentials...")
        az.account_logout()
        # Do not backup/rename SP credentials here if failed (it'll occur recursively)
        ACCOUNT = login_strategy()

    elif ACCOUNT.isSignedIn and not service_principal.isValid:
        # Possibly due to a bad service principal file or insufficient privileges on account
        LOG.error("failed to retrieve valid service principal, signing out...")
        az.account_logout()
        # Prompt manual 'az login' indirectly
        ACCOUNT = login_strategy()

    elif not ACCOUNT.isSignedIn:
        if sh.path_exists(service_principal_path, "f"):
            # Attempt login with service principal credentials found (last chance to be signed-in)
            LOG.debug("attempting login with service principal...")
            ACCOUNT = az.account_login(
                ARGS.tenant,
                f"http://{service_principal.displayName}",
                service_principal.password,
            )
            if not ACCOUNT.isSignedIn:
                if retry:
                    # Will retry recursively only once
                    LOG.warning("Azure login with service principal failed, saving backup and retrying...")
                    sh.backup_file(service_principal_path)
                    ACCOUNT = login_strategy(False)
                else:
                    # This should never occur (theoretically)
                    LOG.error("Azure login with service principal failed again, exiting...")
                    sh.fail_process()
            else:
                LOG.info("you are successfully signed-in Azure!  (on repeat attempt)")
        else:
            # This can occur when signed-in with service principal but needing credentials changed
            LOG.error('not signed-in, enter "az login" to manually login before repeating your previous command')
            # Calling 'az login' in script "works" but the prompt in subprocess causes display issues
            sh.fail_process()

    elif ACCOUNT.isSignedIn and service_principal.isValid:
        LOG.info("you are successfully signed-in Azure!")

    # elif not account.subscription_is_default:
    #     # Ensure subscription is currently active
    #     LOG.debug('activating the selected subscription...')
    #     account_active = az.account_set(ARGS.subscription)
    #     if not account_active:
    #         LOG.error('failed to activate subscription')
    #         sh.fail_process()

    ACCOUNT.login_sp = service_principal
    # LOG.debug(f'ACCOUNT data: {ACCOUNT}')
    # LOG.debug(f'ACCOUNT is signed in: {ACCOUNT.isSignedIn}')
    return ACCOUNT


# This is dependent upon an active PAT in DevOps saved to key vault secret
# Cannot create DevOps PAT by CLI, navigate site manually, go to user settings and select "Personal access tokens"
# https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
def login_devops_pat_strategy() -> str:
    """Method to sign-in an Azure DevOps with PAT"""
    key_vault_name: str = ARGS.login_key_vault
    secret_key: str = "main-devops-pat"
    pat_data: str = ""

    if not ACCOUNT.isSignedIn:
        LOG.error("not signed into account")
        return pat_data

    # Ensure key vault exists
    key_vault = key_vault_strategy(ARGS.location, ARGS.login_resource_group, key_vault_name)
    if not key_vault.isValid:
        LOG.error("failed to retrieve valid key vault details")
        return pat_data

    # Ensure personal access token (PAT) exists in key vault as secret
    key_vault_secret = az.key_vault_secret_get(key_vault_name, secret_key)
    # key_vault_secret = az.key_vault_secret_get(account.auth, key_vault, secret_key)

    if key_vault_secret:
        LOG.info("successfully retrieved DevOps PAT from key vault!")
        pat_data = key_vault_secret
    else:
        LOG.error("failed to retrieve DevOps PAT from key vault")
    return pat_data


# https://docs.microsoft.com/en-us/azure/devops/cli/log-in-via-pat
# Does not use 'az devops login' because environment variable will suffice
def login_devops_strategy():
    """Method to sign-in Azure DevOps account"""
    key_vault: str = ARGS.login_key_vault
    secret_key = "main-devops-pat"

    # Ensure user PAT/credentials exist
    ACCOUNT.devops_pat = login_devops_pat_strategy()
    # LOG.debug(f'PAT data: {ACCOUNT.devops_pat}')

    if not ACCOUNT.devops_pat:
        # This can occur when PAT is neither in local file nor key vault
        LOG.error(
            'failed to retrieve valid PAT, navigate Azure DevOps to manually create a PAT - open "User settings" (2nd icon from right) dropdown and select "Personal access tokens": https://dev.azure.com/david-rachwalik/_usersSettings/tokens'
        )
        LOG.error(f'this PAT should be stored in vault "{key_vault}" as secret "{secret_key}"')
        LOG.error("https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate")
        sh.fail_process()

    LOG.debug("assigning DevOps PAT (personal access token) to environment...")
    az_devops.environment_pat(ACCOUNT.devops_pat)


# # This is dependent upon an active PAT in DevOps saved to key vault secret
# # Cannot create DevOps PAT by CLI, navigate site manually, go to user settings and select "Personal access tokens"
# # https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate
# def login_devops_pat_strategy(pat_path: str) -> str:
#     """Method to sign-in an Azure DevOps with PAT"""
#     key_vault_name: str = ARGS.login_key_vault
#     secret_key: str = 'main-devops-pat'
#     pat_data: str = ''

#     # Ensure user PAT exists in Azure and local
#     if sh.path_exists(pat_path, 'f'):
#         # Gather login info from PAT file
#         LOG.debug('DevOps PAT (personal access token) exists, checking file...')
#         pat_data = sh.read_file(pat_path, True)
#         return pat_data

#     LOG.debug('DevOps PAT (personal access token) missing, checking Azure...')
#     if not ACCOUNT.isSignedIn:
#         return pat_data

#     # Ensure key vault exists
#     key_vault = key_vault_strategy(ARGS.location, ARGS.login_resource_group, key_vault_name)
#     if not key_vault.isValid:
#         LOG.error('failed to retrieve valid key vault details')
#         return pat_data

#     # Ensure personal access token (PAT) exists in key vault as secret
#     key_vault_secret = az.key_vault_secret_get(key_vault_name, secret_key)
#     # key_vault_secret = az.key_vault_secret_get(ACCOUNT.auth, key_vault, secret_key)
#     if not key_vault_secret:
#         LOG.error('failed to retrieve PAT from key vault')
#         return pat_data

#     LOG.debug('successfully retrieved PAT from key vault!')
#     pat_data = key_vault_secret
#     # Store credentials in PAT file
#     az_devops.save_pat(pat_path, pat_data)
#     return pat_data


# Below works, but the login doesn't return False for a bad pat :(
# # https://docs.microsoft.com/en-us/azure/devops/cli/log-in-via-pat
# def login_devops_strategy(retry: bool = True) -> bool:
#     """Method to sign-in Azure DevOps account"""
#     is_devops_signed_in: bool = False
#     user: str = ARGS.login_devops_user
#     key_vault: str = ARGS.login_key_vault
#     secret_key = 'main-devops-pat'
#     # Full filepath to PAT (personal access token)
#     auth_dir: str = ARGS.login_service_principal_dir
#     pat_path: str = sh.join_path(sh.expand_path(auth_dir), 'ado.pat')

#     # Ensure user PAT/credentials exist
#     ACCOUNT.devops_pat = login_devops_pat_strategy(pat_path)
#     LOG.debug(f'PAT data: {ACCOUNT.devops_pat}')

#     # # Check if user is signed-in DevOps (first chance to be signed-in)
#     # LOG.info('checking if already signed-in Azure DevOps...')
#     # # user_is_signed_in: bool = az_devops.user_get(ACCOUNT.devops_pat, user)
#     # is_devops_signed_in: bool = az_devops.login(ACCOUNT.devops_pat)

#     if not ACCOUNT.devops_pat:
#         # This can occur when PAT is neither in local file nor key vault
#         LOG.error('not signed-in Azure DevOps, navigate the following site to manually create a PAT, go to user settings and select "Personal access tokens"')
#         LOG.error('https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate')
#         LOG.error(
#             f'this PAT must be stored in "{key_vault}" as secret "{secret_key}" before repeating your previous command')
#         sh.fail_process()

#     # --- elif used to limit recursive activity ---

#     if ACCOUNT.isSignedIn and not ACCOUNT.devops_pat:
#         # Possibly due to a bad PAT file or insufficient privileges on account
#         LOG.error('failed to retrieve valid PAT, signing out...')
#         az_devops.logout()
#         is_devops_signed_in = login_devops_strategy()

#     elif not is_devops_signed_in:
#         # Attempt login with PAT found (last chance to be signed-in)
#         LOG.debug('attempting DevOps login with PAT (personal access token)...')
#         is_devops_signed_in = az_devops.login(ACCOUNT.devops_pat)
#         if not is_devops_signed_in:
#             if retry:
#                 # Will retry recursively only once
#                 LOG.warning('Azure DevOps login with PAT failed, saving backup and retrying...')
#                 sh.backup_file(pat_path)
#                 is_devops_signed_in = login_devops_strategy(False)
#             else:
#                 LOG.error('Azure DevOps login with PAT failed again, exiting...')
#                 sh.fail_process()

#     elif ACCOUNT.isSignedIn and is_devops_signed_in:
#         LOG.info('you are successfully signed-in Azure DevOps!')

#     return is_devops_signed_in


# ASP.NET Core NuGet Packages (https://www.nuget.org/packages/*)
def _project_packages(strat: str, framework: str) -> List[str]:
    dotnet_packages = []

    # --- Common Development Packages ---
    if framework == "net6.0":
        dotnet_packages.extend(["Microsoft.CodeAnalysis.NetAnalyzers"])
    elif framework == "net5.0":
        dotnet_packages.extend(
            [
                # https://github.com/dotnet/roslyn-analyzers
                # https://docs.microsoft.com/en-us/visualstudio/code-quality/migrate-from-fxcop-analyzers-to-net-analyzers
                "Microsoft.CodeAnalysis.NetAnalyzers",  # 5.x+
                "Microsoft.VisualStudio.Web.BrowserLink",
            ]
        )
    elif framework == "netcoreapp3.1":
        dotnet_packages.extend(
            [
                "Microsoft.CodeAnalysis.FxCopAnalyzers",  # 3.x
                # 'Microsoft.Extensions.Logging.Debug', # No longer required; included in 'Microsoft.AspNetCore.App'
                "Microsoft.VisualStudio.Web.BrowserLink",
            ]
        )

    # --- Database Packages ---
    # Packages needed for scaffolding: [Microsoft.VisualStudio.Web.CodeGeneration.Design, Microsoft.EntityFrameworkCore.SqlServer]
    if strat == "database" or strat == "identity" or strat == "api":
        if framework in ["netcoreapp3.1", "net5.0", "net6.0"]:
            dotnet_packages.extend(
                [
                    "Microsoft.AspNetCore.Diagnostics.EntityFrameworkCore",
                    "Microsoft.EntityFrameworkCore.Tools",
                    "Microsoft.EntityFrameworkCore.Design",  # Install EF Core design package
                    "Microsoft.VisualStudio.Web.CodeGeneration.Design",
                    # Database provider automatically includes Microsoft.EntityFrameworkCore
                    # Install SQL Server database provider
                    "Microsoft.EntityFrameworkCore.SqlServer",
                    # 'Microsoft.EntityFrameworkCore.Sqlite'      # Install SQLite database provider
                ]
            )

    # --- Authentication Packages ---
    if strat == "identity":
        # 'Microsoft.Owin.Security.OpenIdConnect',
        # 'Microsoft.Owin.Security.Cookies',
        # 'Microsoft.Owin.Host.SystemWeb'
        if framework in ["net5.0", "net6.0"]:
            dotnet_packages.extend(
                [
                    "Microsoft.AspNetCore.Identity.EntityFrameworkCore",
                    "Microsoft.AspNetCore.Identity.UI",
                ]
            )
        elif framework == "netcoreapp3.1":
            dotnet_packages.extend(["Microsoft.AspNetCore.Authentication.AzureAD.UI"])  # 3.x

    # --- API Packages ---
    if strat == "api":
        if framework in ["netcoreapp3.1", "net5.0", "net6.0"]:
            dotnet_packages.extend(
                [
                    # 'NSwag.AspNetCore' # Swagger / OpenAPI
                    "Swashbuckle.AspNetCore"
                ]
            )

    dotnet_packages.sort()
    return dotnet_packages


# def application_strategy(tenant: str, root_dir: str, solution: str, project: str, strat: str, environment: str,
#                          framework: str, secret_key: str = '', secret_value: str = '') -> Tuple[bool, bool]:
def application_strategy(
    root_dir: str,
    solution: str,
    project: str,
    strat: str,
    environment: str,
    framework: str,
) -> Tuple[bool, bool]:
    """Method to setup an Azure application"""
    if not ACCOUNT.isSignedIn:
        LOG.debug("account is not signed in")
        return (False, False)
    app_changed = False
    # Determine solution scenario (if a solution directory should exist)
    use_solution_dir = bool(solution and isinstance(solution, str))
    app_dir = sh.join_path(root_dir, solution) if use_solution_dir else sh.join_path(root_dir, project)

    # LOG.info(f"secret_key: {secret_key}")
    # LOG.info(f"secret_value: {secret_value}")

    # strat: [basic, database, identity, api]
    if strat == "identity":
        LOG.info("verifying authentication...")
        # Format name for application object registration
        raw_app_name = f"{project}-{environment}"
        app_name = az.format_resource_name(raw_app_name)
        LOG.info(f"app registration name: {app_name}")

        # Register Azure Active Directory application for project
        ad_app = az.active_directory_application_get(app_name)
        if not ad_app.appId:
            ad_app = az.active_directory_application_set(ACCOUNT.tenantId, app_name)
            if not ad_app.appId:
                LOG.error("failed to register active directory application")
                sh.fail_process()

        # Ensure service principal credentials exist for AD application object registration
        service_principal = service_principal_strategy(ACCOUNT.tenantId, app_name, ad_app.appId)
        # LOG.debug(f'service_principal: {service_principal}')
        # TODO: might need additional test iterations linking AD app to SP with CLI instead of portal

    # # Create solution/repository directory
    # LOG.debug(f'checking for solution dir ({app_dir})...')
    # app_dir_exists = sh.path_exists(app_dir, 'd')
    # if not app_dir_exists:
    #     LOG.warning('could not locate solution directory, creating...')
    #     sh.create_directory(app_dir)
    #     LOG.info(f'successfully created solution directory: {app_dir}')

    LOG.debug(f"Project Name: {project}")

    # Create project directory
    project_dir: str = sh.join_path(app_dir, project) if use_solution_dir else app_dir
    LOG.debug(f"checking for project dir ({project_dir})...")
    project_dir_exists: bool = sh.path_exists(project_dir, "d")
    if not project_dir_exists:
        LOG.warning("could not locate project directory, creating...")
        sh.create_directory(project_dir)
        LOG.info(f"successfully created project directory: {project_dir}")

    # Create ASP.NET Core project
    project_file: str = sh.join_path(project_dir, f"{project}.csproj")
    LOG.debug(f"checking for project ({project_file})...")
    project_exists: bool = sh.path_exists(project_file, "f")
    if not project_exists:
        LOG.warning("could not locate project, creating...")
        project_succeeded: bool = net.project_new(ACCOUNT.tenantId, project_dir, strat, framework)
        LOG.info(f"successfully created project: {project_succeeded}")
        if not project_succeeded:
            LOG.error("project failed to be created, exiting...")
            sh.fail_process()

    # Create ASP.NET Core solution
    solution_file: str = sh.join_path(app_dir, f"{solution}.sln") if use_solution_dir else sh.join_path(app_dir, f"{project}.sln")
    LOG.debug(f"checking for solution ({solution_file})...")
    solution_exists: bool = sh.path_exists(solution_file, "f")
    if not solution_exists:
        LOG.warning("could not locate solution, creating...")
        sln_succeeded = net.solution_new(app_dir, solution) if use_solution_dir else net.solution_new(app_dir, project)
        LOG.info(f"successfully created solution: {sln_succeeded}")
        if not sln_succeeded:
            LOG.error("solution failed to be created, exiting...")
            sh.fail_process()

    # Add ASP.NET Core project to solution
    project_added: bool = net.solution_project_add(solution_file, project_file)
    if not project_added:
        LOG.error(f"failed to add project: {project}")
        sh.fail_process()

    # Add NuGet packages to ASP.NET Core project
    packages_expected: List[str] = _project_packages(strat, framework)
    # LOG.debug(f'NuGet packages_expected: {packages_expected}')
    packages_installed: List[str] = net.project_package_list(project_dir)
    # LOG.debug(f'NuGet packages_installed: {packages_installed}')
    packages_to_install: List[str] = sh.list_differences(packages_expected, packages_installed)
    LOG.debug(f"NuGet packages_to_install: {packages_to_install}")
    for package in packages_to_install:
        package_succeeded: bool = net.project_package_add(project_dir, package)
        if not package_succeeded:
            LOG.error(f"failed to add package: {package}")
            sh.fail_process()

    # https://docs.microsoft.com/en-us/aspnet/core/security/authentication/scaffold-identity#scaffold-identity-into-a-razor-project-without-existing-authorization
    if strat == "identity":
        identity_scaffolded = net.project_identity_scaffold(project_dir)

    return (True, app_changed)


def repository_strategy(
    organization: str,
    root_dir: str,
    app_name: str,
    source: str = "",
    gitignore_path: str = "",
    remote_alias: str = "origin",
) -> bool:
    """Method to setup a GitHub or Azure repository"""
    if source == "github":
        remote_path = f"https://github.com/{organization}/{app_name}"
        LOG.debug(f"source repository (GitHub) remote: {remote_path}")
    elif source == "tfsgit":
        remote_path = f"https://dev.azure.com/{organization}/{app_name}"
        LOG.debug(f"source repository (Azure) remote: {remote_path}")
        return False
    else:
        LOG.error("no source repository")
        return False

    is_bare: bool = not bool(remote_path)
    repo_descriptor: str = "remote, bare" if is_bare else "local, work"
    repo_changed: bool = False

    # Create repository directory
    app_dir: str = sh.join_path(root_dir, app_name)
    LOG.debug(f"checking for repository directory ({app_dir})...")
    app_dir_exists: bool = sh.path_exists(app_dir, "d")
    if not app_dir_exists:
        LOG.warning("could not locate repository directory, creating...")
        sh.create_directory(app_dir)
        LOG.info(f"successfully created repository directory: {app_dir}")

    # Initialize Git repository directory
    repo_dir_exists: bool = git.repo_exists(app_dir, is_bare)
    if repo_dir_exists:
        LOG.debug(f"Successfully found {repo_descriptor} repository")
    else:
        LOG.debug(f"Unable to locate {repo_descriptor} repository")
        display_path: str = app_dir if (is_bare) else f"{app_dir}/.git"
        LOG.info(f"Repository not found ({display_path}), initializing...")
        # Initialize the repository
        (repo_exists, repo_changed) = git.repo_create(app_dir, is_bare)
        if repo_exists:
            LOG.info(f"successfully created {repo_descriptor} repository!")
        else:
            LOG.error(f"Unable to create {repo_descriptor} repository")
            sh.fail_process()

    # Set work repo's remote path to bare repo
    remote_result = git.work_remote(app_dir, remote_path, remote_alias)
    if not remote_result:
        LOG.error("Error occurred updating remote path")
        sh.fail_process()

    # Fetch the latest meta data; increases '.git' directory size
    # git.work_fetch(app_dir)

    # Update '.gitignore' based on hash check
    if len(gitignore_path) > 0:
        file_src = gitignore_path
        file_dest = sh.join_path(app_dir, ".gitignore")
        if sh.path_exists(file_dest, "f"):
            hash_result = sh.match_file(file_src, file_dest)
            if not hash_result:
                LOG.debug('".gitignore" hashes don\'t match, updating...')
                update_result = sh.copy_file(file_src, file_dest)
                if update_result:
                    LOG.debug('".gitignore" was successfully updated!')
                else:
                    LOG.error('".gitignore" failed to be updated')
                    sh.fail_process()
            else:
                LOG.debug('".gitignore" is already up-to-date')
        else:
            LOG.debug('".gitignore" is missing, adding...')
            add_result = sh.copy_file(file_src, file_dest)
            if add_result:
                LOG.debug('".gitignore" was successfully added!')
            else:
                LOG.error('".gitignore" failed to be added')
                sh.fail_process()
    else:
        LOG.debug('skipping ".gitignore" file check')

    return True


# https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-cli#parameters
def _json_to_parameters(parameters: Dict[str, Dict[str, Any]]) -> List[str]:
    out_parameters: List[str] = []
    if not parameters:
        return out_parameters
    # Convert parameters JSON to CLI-ready parameters
    for item in parameters.items():
        # LOG.debug(f'parameters item: {item}')
        # LOG.debug(f'parameters key: {item[0]}')
        if "value" in item[1]:
            # LOG.debug(f'parameters value: {item[1]["value"]}')
            out_parameters.append(f'{item[0]}={item[1]["value"]}')
    return out_parameters


# deployment_group_strategy(account, ARGS.login_service_principal, ARGS.project, ARGS.environment, ARGS.location, ARGS.arm)
def deployment_group_strategy(sp_name: str, project: str, environment: str, location: str, arm: str) -> Tuple[bool, bool]:
    """Method to setup an Azure deployment group"""
    # if not account.isSignedIn: return (az.ResourceGroup(), False)
    deployment_succeeded: bool = False
    deployment_changed: bool = False
    rg_name: str = az.format_resource_name(f"{project}-{environment}")
    # LOG.debug(f'rg_name: {rg_name}')

    # Ensure resource group exists
    resource_group = resource_group_strategy(rg_name, location)
    if not resource_group.isValid:
        LOG.error("failed to create resource group")
        sh.fail_process()

    # Azure Resource Manager steps
    rm_root_path: str = "~/pc-env/ansible_playbooks/roles/azure/resource_manager/deploy/templates"
    template_path: str = sh.join_path(rm_root_path, arm, "azuredeploy.json")
    parameters_path: str = sh.join_path(rm_root_path, arm, "azuredeploy.parameters.json")
    parameters_file: str = sh.read_file(parameters_path)
    parameters_json: Dict[str, Dict[str, Any]] = az.ArmParameters(parameters_file).content

    # When 'objectId' is in parameters, replace its value with service principal's objectId
    if "objectId" in parameters_json and "value" in parameters_json["objectId"]:
        # LOG.debug(f'parameters_json objectId: {parameters_json['objectId']['value']}')
        service_principal = az.service_principal_get(sp_name)
        # LOG.debug(f'service_principal: {service_principal}')
        if service_principal.id:
            parameters_json["objectId"]["value"] = service_principal.id
            # LOG.debug(f'parameters_json objectId: {parameters_json['objectId']['value']}')
            # LOG.debug(f'parameters_json: {parameters_json}')

    # Convert parameters JSON to CLI-ready parameters
    LOG.debug(f"parameters_json: {parameters_json}")
    parameters: List[str] = _json_to_parameters(parameters_json)
    LOG.debug(f"parameters: {parameters}")

    # Ensure deployment group template is valid
    deploy_valid: bool = az.deployment_group_valid(resource_group.name, template_path, parameters)
    if deploy_valid:
        LOG.info("deployment validation has succeeded!")
        deployment_succeeded = az.deployment_group_set(resource_group.name, template_path, parameters)
        if deployment_succeeded:
            LOG.info("deployment to resource group has succeeded!")
            deployment_changed = True
        else:
            LOG.warning("deployment to resource group has failed")
    else:
        LOG.warning("deployment validation has failed")
    return (deployment_succeeded, deployment_changed)


# --- Commands ---


def authenticate():
    """Method that authenticates user to Azure"""
    # Sign-in Azure subscription using service principal
    login_strategy()
    # Generate credential (for Python SDK) from account details
    # ACCOUNT.auth = az.sdk_credential_get('secret', ACCOUNT.tenantId, ACCOUNT.login_sp.appId, ACCOUNT.login_sp.password)
    # az.sdk_credential_environment(ACCOUNT)
    # ACCOUNT.auth = az.sdk_credential_get()
    ACCOUNT.auth = az.sdk_credential_default(ACCOUNT)
    # LOG.debug(f'ACCOUNT auth data: {ACCOUNT.auth}')
    # Sign-in Azure DevOps using PAT
    login_devops_strategy()


def secret():
    """Method to perform actions for creating an Azure key vault secret"""
    key_vault_strategy(ARGS.location, ARGS.resource_group, ARGS.key_vault)
    # Add a [key, secret, certificate] to vault (certificates have annual renewal costs)
    # az.key_vault_secret_set(ARGS.key_vault, ARGS.secret_key, ARGS.secret_value)
    # Set key vault advanced access policies


def sdk_secret():
    """Method to perform actions for creating an Azure key vault secret"""
    main_vault_name = "main-keyvault"
    main_secret_key = "main-devops-pat"
    if ACCOUNT.auth:
        secret_value = az.key_vault_secret_get_new(ACCOUNT.auth, main_vault_name, main_secret_key)
        LOG.debug(f"secret_value: {secret_value}")
    else:
        LOG.debug("Cannot continue without valid credentials, exiting...")
        sh.fail_process()


def app_create():
    """Method to perform actions for creating an Azure application"""
    # application_strategy(ARGS.tenant, ARGS.dotnet_dir, ARGS.solution, ARGS.project,
    #                      ARGS.strat, ARGS.environment, ARGS.framework, ARGS.secret_key, ARGS.secret_value)
    application_strategy(
        ARGS.dotnet_dir,
        ARGS.solution,
        ARGS.project,
        ARGS.strat,
        ARGS.environment,
        ARGS.framework,
    )
    gitignore_path = "~/pc-env/ansible_playbooks/roles/linux/apps/git/init/files/.gitignore"
    # Determine scenario (if repo is inside solution or project directory)
    use_solution_dir = bool(ARGS.solution and isinstance(ARGS.solution, str))
    app_name = ARGS.solution if use_solution_dir else ARGS.project
    repository_strategy(
        ARGS.organization,
        ARGS.dotnet_dir,
        app_name,
        ARGS.source,
        gitignore_path,
        ARGS.remote_alias,
    )


def deploy():
    """Method to perform actions for deploying an application to Azure"""
    # Deploy ARM templates to resource group
    deployment_group_strategy(
        ARGS.login_service_principal,
        ARGS.project,
        ARGS.environment,
        ARGS.location,
        ARGS.arm,
    )

    # project = ARGS.project
    # environment = ARGS.environment
    # rg_name: str = az.format_resource_name(f'{project}-{environment}')
    # LOG.debug(f'rg_name: {rg_name}')
    # LOG.debug(f'script path: {__file__}')

    # Example deployment resource scenarios:
    # - resource group, app service plan, web app service
    # - resource group, app service plan, web app service, sql server, sql database, connection


def pipeline():
    """Method to perform actions for creating an Azure pipeline"""
    LOG.debug('<mock "pipeline" action> -- to be added later if az command gains more pipelines methods')
    # Project pipeline example scenarios:
    # - build csproj, deploy Python (pip) packages
    # - build csproj, deploy NuGet packages
    # - build csproj, deploy ARM templates
    # - build csproj, deploy .zip file to web app service
    # - build csproj, deploy .sql file to sql database


# ------------------------ Main program ------------------------

ARGS = argparse.Namespace()  # for external modules
BASENAME = "app"
# log_file = f'/var/log/{BASENAME}.log'
LOG = log.get_logger(BASENAME)  # Initialize the logger
ACCOUNT = az.Account()

if __name__ == "__main__":
    # if sh.system_platform() == 'windows':
    #     service_principal_dir = '~/.local/az_service_principals'
    # else:
    #     # ~/.local/az_service_principals/{service-principal}.json
    #     service_principal_dir = '~/.local/az_service_principals'
    home_dir = sh.environment_get("HOME")
    service_principal_dir = sh.join_path(home_dir, ".az_service_principals")

    # When 'default' doesn't work, add nargs="?" and const=(same value as default)
    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        # --- Subcommands of 'group' ---
        # group_subparser = parser.add_subparsers(dest="group")
        # group_subparser.add_parser("login")
        # group_subparser.add_parser("secret")
        # group_subparser.add_parser("client")
        # group_subparser.add_parser("deploy")
        # group_subparser.add_parser("pipeline")
        # --- Global defaults ---
        parser.add_argument(
            "group",
            default="login",
            const="login",
            nargs="?",
            choices=["login", "secret", "client", "deploy", "pipeline"],
        )
        parser.add_argument(
            "action",
            default="get",
            const="get",
            nargs="?",
            choices=["get", "set", "remove"],
        )
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        # --- Account defaults ---
        parser.add_argument("--tenant", "-t", default="davidrachwalikoutlook")
        parser.add_argument("--organization", "-o", default="david-rachwalik")
        parser.add_argument("--subscription", "-s", default="Pay-As-You-Go")
        # parser.add_argument('--cert-path', default='~/.local/az_cert.pem')
        parser.add_argument("--service-principal-dir", default=service_principal_dir)
        parser.add_argument("--service-principal", default="")
        # --- Login defaults ---
        parser.add_argument("--login-service-principal-dir", default=service_principal_dir)
        parser.add_argument("--login-service-principal", default="main-rbac-sp")
        parser.add_argument("--login-resource-group", "-G", default="Main")
        parser.add_argument("--login-key-vault", "-V", default="main-keyvault")
        parser.add_argument("--login-devops-user", "-U", default="david-rachwalik@outlook.com")
        # --- Azure Resource defaults ---
        parser.add_argument("--environment", "-e", default="Dev")
        # az account list-locations
        parser.add_argument("--location", "-l", default="southcentralus")
        parser.add_argument("--resource-group", "-g", default="")
        parser.add_argument("--key-vault", "-v", default="")
        parser.add_argument("--secret-key")
        parser.add_argument("--secret-value")
        parser.add_argument("--arm", default="")
        # --- ASP.NET Core Application defaults ---
        parser.add_argument("--dotnet-dir", default="/mnt/e/Repos")
        parser.add_argument("--solution", "-a", default="")
        parser.add_argument("--project", "-p", default="")
        # 'netcoreapp3.1', 'net5.0', 'net6.0'
        parser.add_argument("--framework", "-f", default="net6.0")
        parser.add_argument(
            "--strat",
            default="basic",
            const="basic",
            nargs="?",
            choices=["basic", "database", "identity", "api"],
        )
        # parser.add_argument('--template', default='console', const='console', nargs='?', choices=, ['console', 'webapp', 'webapi', 'xunit'])
        # parser.add_argument('--identity', default='None', const='None', nargs='?', choices=, ['None', 'SingleOrg', 'MultiOrg'])
        # --- Git Repository defaults ---
        parser.add_argument("--source", default="", const="", nargs="?", choices=["github", "tfsgit"])  # tfsgit=Azure
        parser.add_argument("--remote-alias", default="origin")
        parser.add_argument("--remote-path", default="~/my_origin_repo.git")
        parser.add_argument("--gitignore-path", default="")
        return parser.parse_args()

    ARGS = parse_arguments()

    #  Configure the main logger
    LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)
    if ARGS.debug:
        # Configure the shell_boilerplate logger
        _sh_log = log.get_logger("shell_boilerplate")
        log.set_handlers(_sh_log, LOG_HANDLERS)
        sh.ARGS.debug = ARGS.debug
        # Configure the dotnet_boilerplate logger
        _net_log = log.get_logger("dotnet_boilerplate")
        log.set_handlers(_net_log, LOG_HANDLERS)
        net.ARGS.debug = ARGS.debug
        # Configure the azure_boilerplate logger
        _az_log = log.get_logger("azure_boilerplate")
        log.set_handlers(_az_log, LOG_HANDLERS)
        az.ARGS.debug = ARGS.debug
        # Configure the azure_devops_boilerplate logger
        _az_devops_log = log.get_logger("azure_devops_boilerplate")
        log.set_handlers(_az_devops_log, LOG_HANDLERS)
        az_devops.ARGS.debug = ARGS.debug
        # Configure the azure.identity logger (to see which credential is valid)
        # https://stackoverflow.com/questions/64654321/validating-defaultazurecredential-using-python-sdk
        _az_identity_log = log.get_logger("azure.identity")
        LOG_HANDLERS_IDENTITY = log.default_handlers(False, ARGS.log_path)  # INFO
        log.set_handlers(_az_identity_log, LOG_HANDLERS_IDENTITY)

    # ------------------------ Business Logic (group/action) ------------------------

    LOG.debug(f"ARGS: {ARGS}")
    # LOG.debug(f''{ARGS.group}' group detected')
    # LOG.debug(f''{ARGS.action}' action detected')
    LOG.debug("--------------------------------------------------------")

    # --- Run Actions ---

    authenticate()
    LOG.debug(f"ACCOUNT data: {ACCOUNT}")

    # if ARGS.group == 'secret':
    #     secret()
    # elif ARGS.group == 'client':
    #     app_create()
    # elif ARGS.group == 'deploy':
    #     deploy()
    # elif ARGS.group == 'pipeline':
    #     pipeline()

    match ARGS.group:
        case "secret":
            secret()
        case "sdk_secret":
            sdk_secret()
        case "client":
            app_create()
        case "deploy":
            deploy()
        case "pipeline":
            pipeline()
        case _:
            LOG.error("Argument provided is not a valid option")

    # TODO: finish methods for Azure SDK (Python) auth
    # https://portal.azure.com => Microsoft Entra ID => Manage: App Registrations => Display Name: https://main-rbac-sp => Manage: Certificates & Secrets => Client secrets => +New client secret (~1 year)
    # https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app#add-a-client-secret

    # If we get to this point, assume all went well
    LOG.debug("--------------------------------------------------------")
    LOG.debug("--- end point reached :3 ---")
    sh.exit_process()
