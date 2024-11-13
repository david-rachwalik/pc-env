#!/usr/bin/env python
"""Common logic for Azure interactions (with Python SDK)"""

# https://aka.ms/azsdk/python/all
# https://learn.microsoft.com/en-us/azure/developer/python/configure-local-development-environment
# https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-overview
# https://learn.microsoft.com/en-us/azure/developer/python/sdk/examples/azure-sdk-example-resource-group
# https://learn.microsoft.com/en-us/azure/developer/python/sdk/examples/azure-sdk-example-list-resource-groups
# https://learn.microsoft.com/en-us/azure/developer/python/sdk/examples/azure-sdk-example-database

# --- Methods ---
# account:                      account_get, account_list, account_logout, account_login, account_set
# active directory group:       ad_group_get, ad_group_set
# active directory role:        ad_role_get, ad_role_set
# service principal:            service_principal_get, service_principal_rbac_set, service_principal_save
# resource group:               resource_group_get, resource_group_set, resource_group_delete
# key vault:                    key_vault_get, key_vault_set
# key vault secret:             key_vault_secret_get, key_vault_secret_set, key_vault_secret_download
# active directory:             active_directory_application_get, active_directory_application_set
# deployment group:             deployment_group_valid, deployment_group_get, deployment_group_set

# TODO:
# webapp service:               app_set, app_get
# app service plan:             plan_set, plan_get
# resource manager:             rm_set, rm_get
# pipelines:                    pipeline_set, pipeline_get
# SQL database:                 sql_db_set, sql_db_get

import argparse
import re
from dataclasses import dataclass, fields
from typing import Any, Dict, List, Optional, Type, TypeAlias

import azure.identity as azid
import azure.keyvault.secrets as azkv
import azure.mgmt.resource as az_res
import azure.mgmt.subscription as az_sub
# import azure.mgmt.web as az_web
import logging_boilerplate as log
import shell_boilerplate as sh

# https://docs.python.org/3/library/typing.html#typing.TypeAlias
Credential: TypeAlias = azid.DefaultAzureCredential | azid.AzureCliCredential | azid.EnvironmentCredential | azid.ClientSecretCredential

# ------------------------ Data Classes ------------------------


@dataclass()
class ServicePrincipal:
    """Class that tracks Azure service principal details"""
    displayName: str = ''
    appId: str = ''
    id: str = ''

    password: str = ''
    changed: bool = False

    @property
    def isValid(self) -> bool:
        """Getter method to determine whether service principal is valid"""
        return bool(self.appId)


@dataclass(frozen=True)
class AccountUser:
    """Class that tracks Azure user account details"""
    name: str = ''
    type: str = ''


@dataclass()
class Account:
    """Class that tracks Azure account details"""
    tenantId: str = ''  # active directory
    # Microsoft account (*@outlook.com, *@hotmail.com)
    user: Optional[AccountUser] = None
    name: str = ''  # subscription name
    id: str = ''  # subscription id
    isDefault: bool = False  # subscription is default

    auth: Optional[Credential] = None
    login_sp: Optional[ServicePrincipal] = None
    devops_pat: str = ''

    @property
    def isSignedIn(self) -> bool:
        """Getter method to validate whether the user is signed in"""
        return bool(self.tenantId and self.id)

    @property
    def username(self) -> str:
        """Getter method to fetch username from the account user object"""
        result = ''
        if self.user and self.user.name:
            result = self.user.name
        return result

    @property
    def subscription(self) -> str:
        """Getter method to fetch the subscription name"""
        return self.name

    @property
    def subscriptionId(self) -> str:
        """Getter method to fetch the subscription id"""
        return self.id

    @property
    def subscriptionIsDefault(self) -> bool:
        """Getter method to determine whether subscription is set as the default"""
        return self.isDefault


@dataclass()
class AdGroup:
    """Class that tracks Azure Active Directory group"""
    displayName: str = ''  # name
    id: str = ''

    changed: bool = False

    @property
    def isValid(self) -> bool:
        """Getter method to determine whether AD group is valid"""
        return bool(self.displayName)


@dataclass()
class ResourceGroup:
    """Class that tracks Azure resource group details"""
    location: str = ''
    name: str = ''

    changed: bool = False

    @property
    def isValid(self) -> bool:
        """Getter method to determine whether resource group is valid"""
        return bool(self.location and self.name)


@dataclass()
class KeyVault:
    """Class that tracks Azure key vault details"""
    location: str = ''
    name: str = ''
    resourceGroup: str = ''

    changed: bool = False

    @property
    def isValid(self) -> bool:
        """Getter method to determine whether key vault is valid"""
        return bool(self.location and self.name)


# ------------------------ Classes ------------------------

class AzureBase(object):
    """Class that tracks baseline Azure variables"""

    def __repr__(self):
        return vars(self)

    def __str__(self):
        return str(vars(self))


# class ActiveDirectoryApplication_bak(AzureBase):
#     """Class that tracks Azure Active Directory application"""

#     def __init__(self, obj=''):
#         self.name: str = ''
#         self.appId: str = ''  # client_id

#         # Business logic for parsing
#         if obj and isinstance(obj, str):
#             obj = sh.from_json(obj)
#         if sh.is_json_parse(obj):
#             self.appId = obj.appId
#             self.name = obj.displayName
#             self.domain = obj.homepage
#             self.identifierUri = obj.identifierUris[0]
#             self.objectId = obj.objectId
#             self.objectType = obj.objectType
#             self.publisherDomain = obj.publisherDomain
#             self.replyUrl = obj.replyUrls[0]
#             self.signInAudience = obj.signInAudience
#             self.wwwHomepage = obj.wwwHomepage


class ActiveDirectoryApplication(AzureBase):
    """Class that tracks Azure Active Directory application"""

    def __init__(self, data: str = ''):
        self.name: str = ''
        self.appId: str = ''  # client_id
        self.domain: str = ''
        self.identifierUri: str = ''
        self.objectId: str = ''
        self.objectType: str = ''
        self.publisherDomain: str = ''
        self.replyUrl: str = ''
        self.signInAudience: str = ''
        self.wwwHomepage: str = ''

        obj = sh.from_json(data)

        if obj:
            self.name = obj.get('displayName', '')
            self.appId = obj.get('appId', '')
            self.domain = obj.get('homepage', '')
            self.identifierUri = obj.get('identifierUris', [''])[0]
            self.objectId = obj.get('objectId', '')
            self.objectType = obj.get('objectType', '')
            self.publisherDomain = obj.get('publisherDomain', '')
            self.replyUrl = obj.get('replyUrls', [''])[0]
            self.signInAudience = obj.get('signInAudience', '')
            self.wwwHomepage = obj.get('wwwHomepage', '')


class ArmParameters(AzureBase):
    """Class that tracks Azure Resource Manager parameters"""

    def __init__(self, data: str = ''):
        self.content = {}
        # Business logic for parsing
        obj = sh.from_json(data)
        if obj:
            self.content = obj.get('parameters', {})

    def __repr__(self):
        return self.content

    def __str__(self):
        return str(self.content)


# TODO: determine whether needed
@dataclass(frozen=True)
class Subscription:
    """Class that tracks Azure subscription details"""
    display_name: str = ''
    subscription_id: str = ''


# ------------------------ Global Methods ------------------------

# Must conform to the following pattern: '^[0-9a-zA-Z-]+$'
def format_resource_name(raw_name: str, lowercase: bool = True) -> str:
    """Method that formats a string name into a resource name"""
    name = raw_name.lower() if lowercase else raw_name  # lowercase
    # name = re.sub('[^a-zA-Z0-9 \n\.]', '-', raw_name) # old, ignores '.'
    name = re.sub('[^a-zA-Z0-9-]', '-', name)  # replace
    return name


def is_valid_resource_name(raw_name: str, lowercase: bool = True) -> bool:
    """Method that verifies whether a resource name is valid"""
    og_name = str(raw_name)
    formatted_name = format_resource_name(raw_name, lowercase)
    return og_name == formatted_name


def filter_datafields(data: Any, datatype: Type) -> Dict[str, Any]:
    """Method that reduces data to only viable fields based on dataclass provided"""
    # https://stackoverflow.com/questions/54678337/how-does-one-ignore-extra-arguments-passed-to-a-dataclass
    # LOG.debug(f'data.items(): {data.items()}')
    field_names = set(f.name for f in fields(datatype))
    # LOG.debug(f'field_names: {field_names}')
    filtered_data: Dict[str, Any] = {
        k: v for k, v in data.items() if k in field_names}
    # LOG.debug(f'filtered_data: {filtered_data}')
    return filtered_data


def json_to_dataclass(jsonstr: str, datatype: Type) -> Any:
    """Method that handles common actions to convert JSON string to a dataclass"""
    data = sh.from_json(jsonstr)
    # LOG.debug(f'data: {data}')
    # LOG.debug(f'data type: {type(data)}')

    # End early in case of no data available
    if not (data and isinstance(data, dict)):
        return datatype()

    # Reduce data to only viable fields
    filtered_data = filter_datafields(data, datatype)

    # Return the parsed data
    result = datatype(**filtered_data)
    # LOG.debug(f'result: {result}')
    return result


def subscription_details(credential: Credential, name: str) -> Optional[Subscription]:
    """Method that fetches Azure account"""
    sub_client = az_sub.SubscriptionClient(credential)
    sub_list = sub_client.subscriptions.list()
    for sub in sub_list:
        # LOG.debug(f'sub.subscription_id: {sub.subscription_id}')
        # LOG.debug(f'sub.display_name: {sub.display_name}')
        if name == sub.display_name:
            # Reduce data to only viable fields
            filtered_data = filter_datafields(sub, Subscription)
            return Subscription(**filtered_data)
    return None


def sdk_credential_environment(account: Account):
    """Method that sets environment variables based on Azure account"""
    # --- Environment Variables, service principal with secret (based on subscription) ---
    # https://pypi.org/project/azure-identity
    # ID of the application's Azure AD tenant
    sh.environment_set('AZURE_TENANT_ID', account.tenantId)
    if account.login_sp:
        # ID of an Azure AD application
        sh.environment_set('AZURE_CLIENT_ID', account.login_sp.appId)
        # one of the application's client secrets
        sh.environment_set('AZURE_CLIENT_SECRET', account.login_sp.password)


def sdk_credential_get(scope: str = 'default', tenant_id: str = '', client_id: str = '', client_secret: str = '') -> Credential:
    """Method that fetches Azure authentication credential"""
    # https://pypi.org/project/azure-identity
    # https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme
    if scope == 'cli':
        credential = azid.AzureCliCredential()
    if scope == 'env':
        # https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.environmentcredential
        credential = azid.EnvironmentCredential()
    if scope == 'secret':
        # https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.clientsecretcredential
        credential = azid.ClientSecretCredential(tenant_id, client_id, client_secret)
    else:
        # https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential
        credential = azid.DefaultAzureCredential()
    return credential


def sdk_credential_default(account: Account) -> Credential:
    """Method wrapper that handles all steps for obtaining an Azure SDK credential"""
    sdk_credential_environment(account)
    # Generate credential (for Python SDK) from account details
    credential = sdk_credential_get()
    return credential


# --- Account/Subscription Commands ---
# https://docs.microsoft.com/en-us/cli/azure/account

def account_get(subscription: str) -> Account:
    """Method that fetches Azure account"""
    command: List[str] = ['az', 'account',
                          'show', f'--subscription={subscription}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return Account()
    account: Account = json_to_dataclass(process.stdout, Account)
    # LOG.debug(f'account: {account}')
    return account


def account_list() -> Optional[Account]:
    """Method that lists Azure accounts"""
    command: List[str] = ['az', 'account', 'list', '--all']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return None
    # Return the parsed account data
    account: Account = json_to_dataclass(process.stdout, Account)
    # LOG.debug(f'account: {account}')
    return account


def account_logout() -> bool:
    """Method that signs out of Azure account"""
    command: List[str] = ['az', 'logout']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# https://docs.microsoft.com/en-us/cli/azure/reference-index#az_login
# Login with username (service principal) and password (client secret/certificate)
def account_login(tenant: str = '', name: str = '', password: str = '') -> Account:
    """Method that signs into Azure account"""
    command: List[str] = ['az', 'login']
    # az login --service-principal -u <app-url> -p <password-or-cert> --tenant <tenant>
    if tenant and name and password:
        command.append('--service-principal')
        command.append(f'--tenant={tenant}.onmicrosoft.com')
        command.append(f'--username={name}')
        command.append(f'--password={password}')
        command.append('--allow-no-subscriptions')
        command.append('--query=[0]')  # flatten list to dict
    # Print password-safe version of command
    sh.print_command(command, '--password=')
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return Account()
    # Return the parsed account data
    account: Account = json_to_dataclass(process.stdout, Account)
    # LOG.debug(f'account: {account}')
    return account


def account_set(subscription: str) -> bool:
    """Method that sets the default Azure account"""
    command: List[str] = ['az', 'account',
                          'set', f'--subscription={subscription}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- Active Directory (AD) Group Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/group

def ad_group_get(name: str) -> AdGroup:
    """Method that fetches Azure Active Directory group"""
    command: List[str] = ['az', 'ad', 'group', 'show', f'--group={name}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return AdGroup()
    ad_group: AdGroup = json_to_dataclass(process.stdout, AdGroup)
    # LOG.debug(f'ad_group: {ad_group}')
    return ad_group


def ad_group_set(name: str) -> AdGroup:
    """Method that sets the Azure Active Directory group"""
    command: List[str] = ['az', 'ad', 'group', 'create',
                          f'--display-name={name}', f'--mail-nickname={name}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return AdGroup()
    ad_group: AdGroup = json_to_dataclass(process.stdout, AdGroup)
    ad_group.changed = True
    # LOG.debug(f'ad_group: {ad_group}')
    return ad_group


# --- Active Directory (AD) Group Member Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/group/member

def ad_group_member_get(group_name: str, member_id: str) -> bool:
    """Method that fetches Azure Active Directory group member"""
    command: List[str] = ['az', 'ad', 'group', 'member', 'check',
                          f'--group={group_name}', f'--member-id={member_id}', '--query=value']
    sh.print_command(command, '--member-id=')
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0 and process.stdout == 'true'


def ad_group_member_set(group_name: str, member_id: str) -> bool:
    """Method that sets Azure Active Directory group member"""
    command: List[str] = ['az', 'ad', 'group', 'member', 'add',
                          f'--group={group_name}', f'--member-id={member_id}']
    sh.print_command(command, '--member-id=')
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- Role Assignment Commands ---
# https://docs.microsoft.com/en-us/cli/azure/role/assignment
# https://docs.microsoft.com/en-us/azure/role-based-access-control/built-in-roles
# https://docs.microsoft.com/en-us/azure/role-based-access-control/role-assignments-cli

def role_assign_get(assignee_id: str, scope: str = '', role: str = 'Contributor') -> bool:
    """Method that fetches Azure role"""
    # NOTE: do not wrap --role value in '', gets evaluated as part of string
    command: List[str] = ['az', 'role', 'assignment', 'list',
                          f'--assignee={assignee_id}',
                          f'--role={role}', f'--scope={scope}',
                          '--include-inherited', '--include-groups', '--query=[0]']
    sh.print_command(command, '--scope=')  # TODO: use '--assignee=' as well
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


def role_assign_set(assignee_id: str, scope: str = '', role: str = 'Contributor') -> bool:
    """Method that assigns Azure role"""
    # NOTE: do not wrap --role value in '', gets evaluated as part of string
    command: List[str] = ['az', 'role', 'assignment', 'create',
                          f'--assignee={assignee_id}',
                          f'--role={role}', f'--scope={scope}']
    sh.print_command(command, '--scope=')  # TODO: use '--assignee=' as well
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- Service Principal Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/sp

# Always use service principal name (not id)
def service_principal_get(sp_name: str, sp_dir: str = '', tenant: str = '') -> ServicePrincipal:
    """Method that fetches Azure service principal"""
    jsonstr: str = ''
    # Full filepath to service principal data
    if not is_valid_resource_name(sp_name):
        LOG.error('"sp_name" parameter expected as valid resource name')
        sh.fail_process()
    # Gather login info from service principal
    if sp_dir:
        LOG.debug('gathering service principal credentials from file...')
        sp_path = sh.join_path(sh.expand_path(sp_dir), f'{sp_name}.json')
        jsonstr = sh.read_file(sp_path)
    else:
        LOG.debug('gathering service principal from Azure...')
        if tenant:
            command = ['az', 'ad', 'sp', 'show',
                       f'--id=https://{tenant}.onmicrosoft.com/{sp_name}']
        else:
            command = ['az', 'ad', 'sp', 'show', f'--id=http://{sp_name}']
        sh.print_command(command)
        process = sh.run_subprocess(command)
        # sh.log_subprocess(LOG, process, debug=ARGS.debug)
        if process.returncode != 0:
            return ServicePrincipal()
        jsonstr = process.stdout
    # LOG.debug(f'jsonstr: {jsonstr}')
    service_principal: ServicePrincipal = json_to_dataclass(
        jsonstr, ServicePrincipal)
    # LOG.debug(f'service_principal: {service_principal}')
    return service_principal


def service_principal_set(sp_name: str, obj_id: str) -> ServicePrincipal:
    """Method that sets a Azure service principal"""
    # Using '--sdk-auth' produces better output but not available for reset
    command: List[str] = ['az', 'ad', 'sp', 'create', f'--id={obj_id}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return ServicePrincipal()
    service_principal: ServicePrincipal = json_to_dataclass(
        process.stdout, ServicePrincipal)
    service_principal.changed = True
    # LOG.debug(f"service_principal: {service_principal}")
    return service_principal


# https://docs.microsoft.com/en-us/cli/azure/ad/sp#az_ad_sp_create_for_rbac
# https://docs.microsoft.com/en-us/cli/azure/ad/sp/credential#az-ad-sp-credential-reset
def service_principal_rbac_set(sp_name: str, reset: bool = False) -> ServicePrincipal:
    """Method that sets Azure service principal RBAC"""
    # Using '--sdk-auth' produces nice output but is not available for reset
    command: List[str] = ['az', 'ad', 'sp']
    if not reset:
        command.append('create-for-rbac')
        command.append(f'--display-name=http://{sp_name}')
        # returns [appId, displayName, password, tenant]
    else:
        command.append('credential')
        command.append('reset')
        command.append(f'--id=http://{sp_name}')
        # returns [appId, password, tenant]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return ServicePrincipal()
    service_principal: ServicePrincipal = json_to_dataclass(
        process.stdout, ServicePrincipal)
    service_principal.changed = True
    # sp_action = 'reset' if reset else 'created'
    # LOG.info(f'successfully {sp_action} service principal credentials!')
    # LOG.debug(f'service_principal: {service_principal}')
    return service_principal


def service_principal_save(path: str, service_principal: ServicePrincipal) -> bool:
    """Method that saves Azure service principal to a file"""
    data = vars(service_principal)  # same as *.__dict__
    # Remove keys to exclude from JSON file
    data.pop('changed', None)
    data.pop('isValid', None)
    result = sh.save_json(path, data)
    return result


# --- Resource Group Commands ---
# https://learn.microsoft.com/en-us/azure/developer/python/sdk/examples/azure-sdk-example-resource-group
# https://docs.microsoft.com/en-us/cli/azure/group

def resource_group_get_sdk(account: Account, rg_name: str):
    """Method that fetches Azure resource group"""
    if not account.auth:
        return ResourceGroup()
    # Obtain the management object for resources
    resource_client = az_res.ResourceManagementClient(
        account.auth, account.subscriptionId)
    # Provision the resource group
    resource_group = resource_client.resource_groups.get(rg_name)
    LOG.debug(f'resource group: {resource_group}')
    LOG.debug(f'resource group id: {resource_group.id}')
    return resource_group


def resource_group_set_sdk(account: Account, rg_name: str, location: str):
    """Method that sets Azure resource group"""
    if not account.auth:
        return ResourceGroup()
    # Obtain the management object for resources
    resource_client = az_res.ResourceManagementClient(
        account.auth, account.subscriptionId)
    # Provision the resource group
    resource_group = resource_client.resource_groups.create_or_update(
        rg_name, {'location': location}  # type: ignore
    )
    LOG.debug(f'resource group: {resource_group}')
    LOG.debug(f'resource group id: {resource_group.id}')
    return resource_group


def resource_group_get(name: str) -> ResourceGroup:
    """Method that fetches Azure resource group"""
    command: List[str] = ['az', 'group', 'show', f'--name={name}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return ResourceGroup()
    # resource_group = ResourceGroup(process.stdout)
    resource_group: ResourceGroup = json_to_dataclass(
        process.stdout, ResourceGroup)
    # LOG.debug("resource_group: {resource_group}")
    return resource_group


def resource_group_set(name: str, location: str) -> ResourceGroup:
    """Method that sets Azure resource group"""
    command: List[str] = ['az', 'group', 'create',
                          f'--name={name}', f'--location={location}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return ResourceGroup()
    # resource_group = ResourceGroup(process.stdout)
    resource_group: ResourceGroup = json_to_dataclass(
        process.stdout, ResourceGroup)
    resource_group.changed = True
    # LOG.debug("resource_group: {resource_group}")
    return resource_group


# --- Key Vault Commands ---
# https://docs.microsoft.com/en-us/cli/azure/keyvault

def key_vault_get(name: str, resource_group_name: str) -> KeyVault:
    """Method that fetches Azure key vault"""
    command: List[str] = ['az', 'keyvault', 'show',
                          f'--name={name}', f'--resource-group={resource_group_name}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return KeyVault()
    # key_vault = sh.from_json(process.stdout)
    key_vault: KeyVault = json_to_dataclass(process.stdout, KeyVault)
    # LOG.debug("key_vault: {key_vault}")
    return key_vault


# Create a hardened container (vault) in Azure
def key_vault_set(name: str, resource_group_name: str) -> KeyVault:
    """Method that sets Azure key vault"""
    command: List[str] = ['az', 'keyvault', 'create',
                          f'--name={name}', f'--resource-group={resource_group_name}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return KeyVault()
    # key_vault = sh.from_json(process.stdout)
    key_vault: KeyVault = json_to_dataclass(process.stdout, KeyVault)
    key_vault.changed = True
    # LOG.debug("key_vault: {key_vault}")
    return key_vault


# --- Key Vault Secret Commands ---
# https://docs.microsoft.com/en-us/cli/azure/keyvault/secret

def key_vault_secret_get(key_vault: str, secret_key: str) -> str:
    """Method that fetches Azure key vault secret"""
    command: List[str] = ['az', 'keyvault', 'secret', 'show',
                          f'--vault-name={key_vault}', f'--name={secret_key}']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    if process.returncode != 0:
        return ''
    data = sh.from_json(process.stdout)
    if data and isinstance(data, dict) and 'value' in data:
        results = data['value']
    else:
        results = ''
    # LOG.debug("results: {results}")
    return results


def key_vault_secret_get_new(auth: Credential, key_vault: str, secret_key: str) -> str:
    """Method that fetches Azure key vault secret"""
    url = f'https://{key_vault}.vault.azure.net'
    client = azkv.SecretClient(vault_url=url, credential=auth)

    vault_secret = client.get_secret(secret_key)
    # vault_secret = secret_client.set_secret('secret-name', 'secret-value')

    # LOG.debug(vault_secret.name)
    # LOG.debug(vault_secret.value)
    # LOG.debug(vault_secret.properties.version)

    result = vault_secret.value or ''
    # LOG.debug("results: {results}")
    return result


def key_vault_secret_set(key_vault: str, secret_key: str, secret_value: str) -> bool:
    """Method that sets Azure key vault secret"""
    command: List[str] = ['az', 'keyvault', 'secret', 'set',
                          f'--vault-name={key_vault}', f'--name={secret_key}', f'--value={secret_value}']
    # Print password-safe version of command
    sh.print_command(command, '--value=')
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- Active Directory Application Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/app

def active_directory_application_get(app_name: str) -> ActiveDirectoryApplication:
    """Method that fetches Azure Active Directory application"""
    # az_ad_app_project_query: "[?displayName=='{{az_app_registration}}'].{appId: appId, displayName: displayName}"
    command: List[str] = ['az', 'ad', 'app', 'list',
                          f'--query=[?displayName=="{app_name}"] | [0]']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    ad_app = ActiveDirectoryApplication(process.stdout)
    LOG.debug(f'ad_app: {ad_app}')
    return ad_app


def active_directory_application_set(tenant: str, app_name: str, app_id: str = '') -> ActiveDirectoryApplication:
    """Method that sets Azure Active Directory application"""
    az_ad_domain: str = f'https://{tenant}.onmicrosoft.com'
    az_ad_identifier_url: str = f'{az_ad_domain}/{app_name}'
    app_domain: str = 'https://localhost:5001'
    az_ad_reply_url: str = f'{app_domain}/signin-oidc'

    if app_id:
        LOG.info('updating Azure AD application object registration...')
        command = ['az', 'ad', 'app', 'update', f'--id={app_id}']
    else:
        LOG.info('creating Azure AD application object registration...')
        command = ['az', 'ad', 'app', 'create']

    # --display-name {{az_app_registration}}
    # --homepage {{app_domain}}
    # --identifier-uris {{az_ad_identifier_urls | join(' ')}}
    # --reply-urls {{az_ad_reply_urls | join(' ')}}
    # --available-to-other-tenants {{app_authentication == 'MultiOrg'}}
    # # --required-resource-accesses {{az_ad_app_permissions | to_json}}
    # # --oauth2-allow-implicit-flow true
    # # TODO: add --app-roles once authentication testing is further
    command.extend([
        f'--display-name={app_name}',
        f'--homepage={app_domain}',
        f'--identifier-uris={az_ad_identifier_url}',
        f'--reply-urls={az_ad_reply_url}',
        '--available-to-other-tenants=true'
    ])
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    ad_app = ActiveDirectoryApplication(process.stdout)
    LOG.debug(f'ad_app: {ad_app}')
    return ad_app


# --- Deployment Group Commands ---
# https://docs.microsoft.com/en-us/cli/azure/deployment/group
# https://github.com/Azure-Samples/azure-samples-python-management/blob/main/samples/resources/manage_resource_deployment.py

def deployment_group_valid_sdk(account: Account, rg_name: str, template_path: str, parameters: Optional[List[str]] = None, deploy_name: str = 'Main') -> bool:
    """Method that validates Azure deployment group"""
    if not account.auth:
        return False

    # Create client
    resource_client = az_res.ResourceManagementClient(
        credential=account.auth,
        subscription_id=account.subscriptionId
    )
    LOG.debug(f'client: {resource_client}')

    # Validate deployment
    validation = resource_client.deployments.begin_validate(  # type: ignore
        rg_name,
        deploy_name,
        {
            'properties': {
                'mode': 'Incremental',
                # 'template': template,
                # 'parameters': {'location': {'value': 'West US'}}
                'template': template_path,
                'parameters': parameters
            }
        }  # type: ignore
    ).result()
    LOG.debug(f'Validate deployment:\n{validation}')
    return bool(validation)


def deployment_group_valid(rg_name: str, template_path: str, parameters: Optional[List[str]] = None, deploy_name: str = 'Main') -> bool:
    """Method that validates Azure deployment group"""
    command: List[str] = ['az', 'deployment', 'group', 'validate',
                          f'--name={deploy_name}',
                          f'--resource-group={rg_name}',
                          f'--template-file={template_path}']
    if parameters:
        command.append('--parameters')
        command.extend(parameters)
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


def deployment_group_get(rg_name: str, template_path: str, parameters: Optional[List[str]] = None, deploy_name: str = 'Main') -> bool:
    """Method that fetches Azure deployment group"""
    if parameters is None:
        parameters = []
    command: List[str] = ['az', 'deployment', 'group', 'show',
                          f'--name={deploy_name}',
                          f'--resource-group={rg_name}',
                          f'--template-file={template_path}',
                          # f'--parameters={parameters}',
                          ]
    if parameters:
        command.append('--parameters')
        command.extend(parameters)
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


def deployment_group_set(rg_name: str, template_path: str, parameters: Optional[List[str]] = None, deploy_name: str = 'Main') -> bool:
    """Method that sets Azure deployment group"""
    if parameters is None:
        parameters = []
    command: List[str] = ['az', 'deployment', 'group', 'create',
                          f'--name={deploy_name}',
                          f'--resource-group={rg_name}',
                          f'--template-file={template_path}'
                          # f'--parameters={parameters}'
                          ]
    if parameters:
        command.append('--parameters')
        command.extend(parameters)
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# ------------------------ Main Program ------------------------

ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
BASENAME = 'azure_boilerplate'
LOG: log.Logger = log.get_logger(BASENAME)  # Initialize the logger

if __name__ == '__main__':
    # Returns argparse.Namespace; to pass into function, use **vars(self.ARGS)
    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--log-path', default='')
        return parser.parse_args()
    ARGS = parse_arguments()

    #  Configure the main logger
    LOG_HANDLERS: List[log.LogHandlerOptions] = log.default_handlers(
        ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)
    if ARGS.debug:
        # Configure the shell_boilerplate logger
        _sh_log = log.get_logger('shell_boilerplate')
        log.set_handlers(_sh_log, LOG_HANDLERS)
        sh.ARGS.debug = ARGS.debug

    LOG.debug(f'ARGS: {ARGS}')
    LOG.debug('------------------------------------------------')

    # --- Usage Example ---
    # python ~/.local/lib/python3.6/site-packages/azure_boilerplate.py --debug
    # py $Env:AppData\Python\Python311\site-packages\boilerplates\azure_boilerplate.py --debug
