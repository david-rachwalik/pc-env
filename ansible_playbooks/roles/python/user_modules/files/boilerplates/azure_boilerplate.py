#!/usr/bin/env python

# Basename: azure_boilerplate
# Description: Common business logic for Azure resources
# Version: 1.0.3
# VersionDate: 19 Oct 2021

# --- Global Azure Classes ---
# Account:                      is_signed_in, tenant_id, account_user, subscription, subscription_id, subscription_is_default
# ServicePrincipal:             name, appId, password

# --- Global Azure Methods ---
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

# import json, time, re
from typing import List, Optional, Tuple

import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Classes ------------------------


class AzureBase(object):
    def __repr__(self):
        return vars(self)

    def __str__(self):
        return str(vars(self))


class Account(AzureBase):
    def __init__(self, obj=""):
        self.is_signed_in: bool = False
        self.tenant_id: str = ""  # active directory
        self.account_user: str = ""  # Microsoft account (*@outlook.com, *@hotmail.com)
        self.subscription: str = ""
        self.subscription_id: str = ""
        self.subscription_is_default: bool = False
        self.devops_pat: str = ""

        # Business logic for parsing
        if obj and isinstance(obj, str):
            obj = sh.json_parse(obj)
        # Sometimes the output is a list (e.g. 'az login')
        # TODO: search by subscription name instead of always first result
        if obj and isinstance(obj, list):
            obj = obj[0]
        if sh.is_json_parse(obj):
            self.tenant_id = obj.tenantId
            self.account_user = obj.user.name
            self.subscription = obj.name
            self.subscription_id = obj.id
            self.subscription_is_default = obj.isDefault
            self.is_signed_in = bool(self.tenant_id and self.subscription_id)


class AdGroup(AzureBase):
    def __init__(self, obj=""):
        self.is_valid: bool = False
        self.name: str = ""

        # Business logic for parsing
        if obj and isinstance(obj, str):
            obj = sh.json_parse(obj)
        if sh.is_json_parse(obj):
            self.name = obj.displayName
            self.mail_nickname = obj.mailNickname
            self.type = obj.objectType  # Group
            self.id = obj.objectId
            self.is_valid = bool(self.name)


# NOTE: match attribute names to stdout for consistent JSON serialization
class ServicePrincipal(AzureBase):
    def __init__(self, obj="", sp_name=""):
        self.name: str = sp_name
        self.appId: str = ""
        self.objectId: str = ""
        self.password: str = ""

        # Business logic for parsing
        if obj and isinstance(obj, str):
            obj = sh.json_parse(obj)
        if sh.is_json_parse(obj):
            keys = obj.keys()

            # keys for 'az ad sp show', 'az ad sp create-for-rbac', 'az ad sp credential reset'
            # - [name, appId,    password,     tenant]
            # keys for 'az ad sp create-for-rbac --sdk-auth'
            # - [      clientId, clientSecret, tenantId]

            if "name" in keys:
                self.name = sh.path_basename(obj.name)
            if "appId" in keys:
                self.appId = obj.appId
            if "objectId" in keys:
                self.objectId = obj.objectId
            if "password" in keys:
                self.password = obj.password


class ResourceGroup(AzureBase):
    def __init__(self, obj=""):
        self.is_valid: bool = False
        self.name: str = ""
        self.location: str = ""

        # Business logic for parsing
        if obj and isinstance(obj, str):
            obj = sh.json_parse(obj)
        if sh.is_json_parse(obj):
            self.location = obj.location
            self.name = obj.name
            self.is_valid = bool(self.location and self.name)


class ActiveDirectoryApplication(AzureBase):
    def __init__(self, obj=""):
        self.name: str = ""
        self.appId: str = ""  # client_id

        # Business logic for parsing
        if obj and isinstance(obj, str):
            obj = sh.json_parse(obj)
        if sh.is_json_parse(obj):
            self.appId = obj.appId
            self.name = obj.displayName
            self.domain = obj.homepage
            self.identifierUri = obj.identifierUris[0]
            self.objectId = obj.objectId
            self.objectType = obj.objectType
            self.publisherDomain = obj.publisherDomain
            self.replyUrl = obj.replyUrls[0]
            self.signInAudience = obj.signInAudience
            self.wwwHomepage = obj.wwwHomepage


class ArmParameters(AzureBase):
    def __init__(self, obj=""):
        self.content = {}
        # Business logic for parsing
        if obj and isinstance(obj, str):
            obj = sh.json_parse(obj)
        if sh.is_json_parse(obj):
            self.content = obj.parameters
            if not self.content:
                self.content = {}

    def __repr__(self):
        return self.content

    def __str__(self):
        return str(self.content)


# ------------------------ Global Methods ------------------------

# --- Account/Subscription Commands ---
# https://docs.microsoft.com/en-us/cli/azure/account


def account_get(subscription: str) -> Account:
    if not (subscription and isinstance(subscription, str)):
        TypeError("'subscription' parameter expected as string")
    command: List[str] = [
        "az",
        "account",
        "show",
        "--subscription={0}".format(subscription),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc != 0:
        return Account()
    # Return the parsed account data
    results: Account = Account(stdout)
    # _log.debug("results: {0}".format(results))
    return results


def account_list() -> Account:
    command: List[str] = ["az", "account", "list", "--all"]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc != 0:
        return Account()
    # Return the parsed account data
    results: Account = Account(stdout)
    # _log.debug("results: {0}".format(results))
    return results


def account_logout() -> bool:
    command: List[str] = ["az", "logout"]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return rc == 0


# https://docs.microsoft.com/en-us/cli/azure/reference-index#az_login
# Login with username (service principal) and password (client secret/certificate)
def account_login(
    tenant: Optional[str] = "", name: Optional[str] = "", password: Optional[str] = ""
) -> Account:
    command: List[str] = ["az", "login"]
    # az login --service-principal -u <app-url> -p <password-or-cert> --tenant <tenant>
    if tenant and name and password:
        command.append("--service-principal")
        command.append("--tenant={0}.onmicrosoft.com".format(tenant))
        command.append("--username=http://{0}".format(name))
        command.append("--password={0}".format(password))
        command.append("--allow-no-subscriptions")
    # Print password-safe version of command
    sh.print_command(command, "--password=")
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc != 0:
        return Account()
    # Return the parsed account data
    results: Account = Account(stdout)
    # _log.debug("results: {0}".format(results))
    return results


def account_set(subscription: str) -> bool:
    if not (subscription and isinstance(subscription, str)):
        TypeError("'subscription' parameter expected as string")
    command: List[str] = [
        "az",
        "account",
        "set",
        "--subscription={0}".format(subscription),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return rc == 0


# --- Active Directory (AD) Group Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/group


def ad_group_get(name: str) -> AdGroup:
    command: List[str] = ["az", "ad", "group", "show", "--group={0}".format(name)]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    ad_group: AdGroup = AdGroup(stdout)
    _log.debug("ad_group: {0}".format(ad_group))
    return ad_group


def ad_group_set(name: str) -> Tuple[AdGroup, bool]:
    ad_group: AdGroup = AdGroup()
    group_changed: bool = False
    command: List[str] = [
        "az",
        "ad",
        "group",
        "create",
        "--display-name={0}".format(name),
        "--mail-nickname={0}".format(name),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc == 0:
        ad_group = AdGroup(stdout)
        group_changed = True
    _log.debug("ad_group: {0}".format(ad_group))
    return (ad_group, group_changed)


# --- Active Directory (AD) Group Member Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/group/member


def ad_group_member_get(name: str, member_id: str) -> bool:
    if not (name and isinstance(name, str)):
        TypeError("'name' parameter expected as string")
    if not (member_id and isinstance(member_id, str)):
        TypeError("'member_id' parameter expected as string")
    command: List[str] = [
        "az",
        "ad",
        "group",
        "member",
        "check",
        "--group={0}".format(name),
        "--member-id={0}".format(member_id),
        "--query=value",
    ]
    sh.print_command(command, "--member-id=")
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0 and stdout == "true")


def ad_group_member_set(name: str, member_id: str) -> bool:
    if not (name and isinstance(name, str)):
        TypeError("'name' parameter expected as string")
    if not (member_id and isinstance(member_id, str)):
        TypeError("'member_id' parameter expected as string")
    command: List[str] = [
        "az",
        "ad",
        "group",
        "member",
        "add",
        "--group={0}".format(name),
        "--member-id={0}".format(member_id),
    ]
    sh.print_command(command, "--member-id=")
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


# --- Role Assignment Commands ---
# https://docs.microsoft.com/en-us/cli/azure/role/assignment
# https://docs.microsoft.com/en-us/azure/role-based-access-control/built-in-roles
# https://docs.microsoft.com/en-us/azure/role-based-access-control/role-assignments-cli


def role_assign_get(assignee_id: str, scope="", role="Contributor") -> bool:
    if not (assignee_id and isinstance(assignee_id, str)):
        TypeError("'assignee_id' parameter expected as string")
    if not (scope and isinstance(scope, str)):
        TypeError("'scope' parameter expected as string")
    # NOTE: do not wrap --role value in '', gets evaluated as part of string
    command: List[str] = [
        "az",
        "role",
        "assignment",
        "list",
        "--assignee={0}".format(assignee_id),
        "--role={0}".format(role),
        "--scope={0}".format(scope),
        "--include-inherited",
        "--include-groups",
        "--query=[0]",
    ]
    sh.print_command(command, "--scope=")
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


def role_assign_set(assignee_id: str, scope="", role="Contributor") -> bool:
    if not (assignee_id and isinstance(assignee_id, str)):
        TypeError("'assignee_id' parameter expected as string")
    if not (scope and isinstance(scope, str)):
        TypeError("'scope' parameter expected as string")
    # NOTE: do not wrap --role value in '', gets evaluated as part of string
    command: List[str] = [
        "az",
        "role",
        "assignment",
        "create",
        "--assignee={0}".format(assignee_id),
        "--role={0}".format(role),
        "--scope={0}".format(scope),
    ]
    sh.print_command(command, "--scope=")
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


# --- Service Principal Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/sp


# Always use service principal name (not id)
def service_principal_get(
    sp_name: str, sp_dir: Optional[str] = "", tenant: Optional[str] = ""
) -> ServicePrincipal:
    if not (sp_name and isinstance(sp_name, str)):
        TypeError("'sp_name' parameter expected as string")
    # Full filepath to service principal data
    if not sh.valid_resource(sp_name):
        _log.error("'sp_name' parameter expected as valid resource name")
        sh.process_fail()
    # Gather login info from service principal
    if sp_dir:
        _log.debug("gathering service principal credentials from file...")
        sp_path = sh.path_join(sh.path_expand(sp_dir), "{0}.json".format(sp_name))
        stdout = sh.file_read(sp_path)
    else:
        _log.debug("gathering service principal from Azure...")
        # if not sp_name.startswith("http://"): sp_name = "http://{0}".format(sp_name)
        if tenant:
            command = [
                "az",
                "ad",
                "sp",
                "show",
                "--id=https://{0}.onmicrosoft.com/{1}".format(tenant, sp_name),
            ]
        else:
            command = ["az", "ad", "sp", "show", "--id=http://{0}".format(sp_name)]
        sh.print_command(command)
        (stdout, stderr, rc) = sh.subprocess_run(command)
        # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
        if rc != 0:
            return ServicePrincipal()
    # Return the parsed service principal data
    service_principal: ServicePrincipal = ServicePrincipal(stdout, sp_name)
    # _log.debug("service_principal: {0}".format(service_principal))
    return service_principal


def service_principal_set(sp_name: str, obj_id: str) -> ServicePrincipal:
    if not (sp_name and isinstance(sp_name, str)):
        TypeError("'sp_name' parameter expected as string")
    if not (obj_id and isinstance(obj_id, str)):
        TypeError("'obj_id' parameter expected as string")
    # Using '--sdk-auth' produces better output but not available for reset
    command: List[str] = ["az", "ad", "sp", "create", "--id={0}".format(obj_id)]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc == 0 and stdout:
        service_principal = ServicePrincipal(stdout, sp_name)
        return service_principal
    else:
        return ServicePrincipal()


# https://docs.microsoft.com/en-us/cli/azure/ad/sp#az_ad_sp_create_for_rbac
# https://docs.microsoft.com/en-us/cli/azure/ad/sp/credential#az-ad-sp-credential-reset
# az ad sp create-for-rbac --name {service-principal} --skip-assignment --sdk-auth > ~/.local/local-sp.json
def service_principal_rbac_set(
    key_vault: str, sp_name: str, reset: Optional[bool] = False
) -> ServicePrincipal:
    if not (key_vault and isinstance(key_vault, str)):
        TypeError("'key_vault' parameter expected as string")
    if not (sp_name and isinstance(sp_name, str)):
        TypeError("'sp_name' parameter expected as string")
    # Using '--sdk-auth' produces better output but not available for reset
    command: List[str] = ["az", "ad", "sp"]
    if not reset:
        command.append("create-for-rbac")
    else:
        command.append("credential")
        command.append("reset")
    command.append("--name={0}".format("http://{0}".format(sp_name)))
    if not reset:
        command.append("--skip-assignment")
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc == 0 and stdout:
        _log.info(
            "successfully {0} service principal credentials!".format(
                "reset" if reset else "created"
            )
        )
        service_principal = ServicePrincipal(stdout, sp_name)
        return service_principal
    else:
        return ServicePrincipal()


# # https://docs.microsoft.com/en-us/cli/azure/ad/sp#az_ad_sp_create_for_rbac
# # az ad sp create-for-rbac --name ServicePrincipalName --create-cert --cert CertName --keyvault VaultName
# def service_principal_rbac_set_certificate(cert, key_vault):
#     command = ["az", "ad", "sp", "create-for-rbac"]
#     command.append("--name={0}".format("http://{0}".format(cert)))
#     command.append("--create-cert")
#     command.append("--cert={0}".format(cert))
#     command.append("--keyvault={0}".format(key_vault))
#     sh.print_command(command)
#     (stdout, stderr, rc) = sh.subprocess_run(command)
#     # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
#     service_principal = sh.json_parse(stdout)
#     # _log.debug("service_principal: {0}".format(service_principal))
#     # Same output as key vault secret
#     return service_principal


# def service_principal_save(path, service_principal):
#     if not (path and isinstance(path, str)): TypeError("'path' parameter expected as string")
#     if not isinstance(service_principal, ServicePrincipal): TypeError("'service_principal' parameter expected as ServicePrincipal")
#     # Handle previous service principal if found
#     if sh.path_exists(path, "f"): backup_path = sh.file_backup(path)
#     # https://stackoverflow.com/questions/39491420/python-jsonexpecting-property-name-enclosed-in-double-quotes
#     # Valid JSON syntax uses quotation marks; single quotes only valid in string
#     # https://stackoverflow.com/questions/43509448/building-json-file-out-of-python-objects
#     _log.info("storing service principal credentials...")
#     file_ready = json.dumps(service_principal.__dict__, indent=4)
#     sh.file_write(path, file_ready)
#     _log.info("successfully saved service principal credentials!")


def service_principal_save(path: str, service_principal: ServicePrincipal):
    if not (path and isinstance(path, str)):
        TypeError("'path' parameter expected as string")
    if not isinstance(service_principal, ServicePrincipal):
        TypeError("'service_principal' parameter expected as ServicePrincipal")
    _log.info("storing service principal credentials...")
    sh.json_save(path, str(service_principal.__dict__))
    _log.info("successfully saved service principal credentials!")


# --- Resource Group Commands ---
# https://docs.microsoft.com/en-us/cli/azure/group
# * Identical output for [resource_group_get, resource_group_set]


def resource_group_get(name: str) -> ResourceGroup:
    command: List[str] = ["az", "group", "show", "--name={0}".format(name)]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    resource_group = ResourceGroup(stdout)
    # _log.debug("resource_group: {0}".format(resource_group))
    return resource_group


def resource_group_set(name: str, location: str) -> ResourceGroup:
    command: List[str] = [
        "az",
        "group",
        "create",
        "--name={0}".format(name),
        "--location={0}".format(location),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    resource_group = ResourceGroup(stdout)
    # _log.debug("resource_group: {0}".format(resource_group))
    return resource_group


# --- Key Vault Commands ---
# https://docs.microsoft.com/en-us/cli/azure/keyvault


def key_vault_get(resource_group: str, key_vault: str):
    if not (resource_group and isinstance(resource_group, str)):
        TypeError("'resource_group' parameter expected as string")
    if not (key_vault and isinstance(key_vault, str)):
        TypeError("'key_vault' parameter expected as string")
    command: List[str] = [
        "az",
        "keyvault",
        "show",
        "--name={0}".format(key_vault),
        "--resource-group={0}".format(resource_group),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    results = sh.json_parse(stdout)
    # _log.debug("results: {0}".format(results))
    return results


# Create a hardened container (vault) in Azure
def key_vault_set(resource_group: str, key_vault: str):
    if not (resource_group and isinstance(resource_group, str)):
        TypeError("'resource_group' parameter expected as string")
    if not (key_vault and isinstance(key_vault, str)):
        TypeError("'key_vault' parameter expected as string")
    command: List[str] = [
        "az",
        "keyvault",
        "create",
        "--name={0}".format(key_vault),
        "--resource-group={0}".format(resource_group),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    results = sh.json_parse(stdout)
    # _log.debug("results: {0}".format(results))
    return results


# --- Key Vault Secret Commands ---
# https://docs.microsoft.com/en-us/cli/azure/keyvault/secret


def key_vault_secret_get(key_vault: str, secret_key: str):
    command: List[str] = [
        "az",
        "keyvault",
        "secret",
        "show",
        "--vault-name={0}".format(key_vault),
        "--name={0}".format(secret_key),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc != 0:
        return ""
    results = sh.json_parse(stdout)
    # _log.debug("results: {0}".format(results))
    return results


def key_vault_secret_set(key_vault: str, secret_key: str, secret_value: str):
    _log.info("storing key vault secret...")
    command: List[str] = [
        "az",
        "keyvault",
        "secret",
        "set",
        "--vault-name={0}".format(key_vault),
        "--name={0}".format(secret_key),
        "--value={0}".format(secret_value),
    ]

    # command_str = str.join(" ", command)
    # command_str = command_str.split("--value=", 1)
    # command_str = "{0}--value=*".format(command_str[0]) # password hidden from log
    # _log.debug("command => {0}".format(command_str))

    # Print password-safe version of command
    sh.print_command(command, "--value=")
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc != 0:
        return ""
    results = sh.json_parse(stdout)
    # _log.debug("results: {0}".format(results))
    return results


# https://github.com/MicrosoftDocs/azure-docs/issues/14761
# https://github.com/Azure/azure-cli/issues/7489
# az keyvault secret download --file <mySecretCert.pem> --encoding base64 --name --vault-name
# openssl pkcs12 -in <mySecretCert.pem> -out <mycert.pem> -nodes -passout
def key_vault_secret_download(cert_path: str, key_vault: str, secret_key: str) -> bool:
    temp_cert_path: str = sh.path_join(
        sh.path_dir(cert_path), "temp-{0}".format(sh.path_basename(cert_path))
    )
    backup_path: str = ""
    # Handle previous certification files if found
    if sh.path_exists(temp_cert_path, "f"):
        sh.file_delete(temp_cert_path)
    if sh.path_exists(cert_path, "f"):
        backup_path = sh.file_backup(cert_path)

    # Download secret from key vault
    command: List[str] = [
        "az",
        "keyvault",
        "secret",
        "download",
        "--file={0}".format(temp_cert_path),
        "--encoding=base64",
        "--vault-name={0}".format(key_vault),
        "--name={0}".format(secret_key),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    if rc != 0:
        return False
    # Convert to proper format using OpenSSL
    # https://www.openssl.org/docs/man1.1.1/man1/openssl.html
    # command: List[str] = ["openssl", "pkcs12", "-in={0}".format(temp_cert_path), "-out={0}".format(cert_path), "-passout"]
    command: List[str] = [
        "openssl",
        "pkcs12",
        "-in={0}".format(temp_cert_path),
        "-out={0}".format(cert_path),
        "-nodes",
        "-password pass:''",
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)

    # Remove recent backup if hash matches downloaded secret
    if backup_path:
        match = sh.file_match(cert_path, backup_path)
        if match:
            sh.file_delete(backup_path)

    return rc == 0


# --- Active Directory Application Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ad/app


def active_directory_application_get(app_name: str) -> ActiveDirectoryApplication:
    command: List[str] = [
        "az",
        "ad",
        "app",
        "list",
        "--query=[?displayName=='{0}'] | [0]".format(app_name),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    ad_app = ActiveDirectoryApplication(stdout)
    _log.debug("ad_app: {0}".format(ad_app))
    return ad_app


def active_directory_application_set(
    tenant: str, app_name: str, app_id: Optional[str] = ""
) -> ActiveDirectoryApplication:
    if not (tenant and isinstance(tenant, str)):
        TypeError("'tenant' parameter expected as string")
    if not (app_name and isinstance(app_name, str)):
        TypeError("'app_name' parameter expected as string")
    if not (isinstance(app_id, str)):
        TypeError("'app_id' parameter expected as string")
    az_ad_domain: str = "https://{0}.onmicrosoft.com".format(tenant)
    az_ad_identifier_url: str = "{0}/{1}".format(az_ad_domain, app_name)
    app_domain: str = "https://localhost:5001"
    az_ad_reply_url: str = "{0}/signin-oidc".format(app_domain)

    if app_id:
        _log.info("updating Azure AD application object registration...")
        command = ["az", "ad", "app", "update", "--id={0}".format(app_id)]
    else:
        _log.info("creating Azure AD application object registration...")
        command = ["az", "ad", "app", "create"]

    # --display-name {{az_app_registration}}
    # --homepage {{app_domain}}
    # --identifier-uris {{az_ad_identifier_urls | join(' ')}}
    # --reply-urls {{az_ad_reply_urls | join(' ')}}
    # --available-to-other-tenants {{app_authentication == 'MultiOrg'}}
    # # --required-resource-accesses {{az_ad_app_permissions | to_json}}
    # # --oauth2-allow-implicit-flow true
    # # TODO: add --app-roles once authentication testing is further
    command.extend(
        [
            "--display-name={0}".format(app_name),
            "--homepage={0}".format(app_domain),
            "--identifier-uris={0}".format(az_ad_identifier_url),
            "--reply-urls={0}".format(az_ad_reply_url),
            "--available-to-other-tenants=true",
        ]
    )
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    ad_app = ActiveDirectoryApplication(stdout)
    _log.debug("ad_app: {0}".format(ad_app))
    return ad_app


# --- Deployment Group Commands ---
# https://docs.microsoft.com/en-us/cli/azure/deployment/group


def deployment_group_valid(
    rg_name: str,
    template_path: str,
    parameters: Optional[List[str]] = None,
    deploy_name: Optional[str] = "Main",
) -> bool:
    if not (rg_name and isinstance(rg_name, str)):
        TypeError("'rg_name' parameter expected as string")
    if not (template_path and isinstance(template_path, str)):
        TypeError("'template_path' parameter expected as string")
    if isinstance(parameters, type(None)):
        parameters = []
    # if not (parameters and isinstance(parameters, str)): TypeError("'parameters' parameter expected as string")
    if not sh.is_list_of_strings(parameters):
        TypeError("'parameters' parameter expected as list of strings")
    if not (deploy_name and isinstance(deploy_name, str)):
        TypeError("'deploy_name' parameter expected as string")
    command: List[str] = [
        "az",
        "deployment",
        "group",
        "validate",
        "--name={0}".format(deploy_name),
        "--resource-group={0}".format(rg_name),
        "--template-file={0}".format(template_path),
        # "--parameters={0}".format(parameters),
    ]
    if parameters:
        command.append("--parameters")
        command.extend(parameters)
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return rc == 0


def deployment_group_get(
    rg_name: str,
    template_path: str,
    parameters: Optional[List[str]] = None,
    deploy_name: Optional[str] = "Main",
) -> bool:
    if not (rg_name and isinstance(rg_name, str)):
        TypeError("'rg_name' parameter expected as string")
    if not (template_path and isinstance(template_path, str)):
        TypeError("'template_path' parameter expected as string")
    if isinstance(parameters, type(None)):
        parameters = []
    # if not (parameters and isinstance(parameters, str)): TypeError("'parameters' parameter expected as string")
    if not sh.is_list_of_strings(parameters):
        TypeError("'parameters' parameter expected as list of strings")
    if not (deploy_name and isinstance(deploy_name, str)):
        TypeError("'deploy_name' parameter expected as string")
    command: List[str] = [
        "az",
        "deployment",
        "group",
        "show",
        "--name={0}".format(deploy_name),
        "--resource-group={0}".format(rg_name),
        "--template-file={0}".format(template_path),
        # "--parameters={0}".format(parameters),
    ]
    if parameters:
        command.append("--parameters")
        command.extend(parameters)
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return rc == 0


def deployment_group_set(
    rg_name: str,
    template_path: str,
    parameters: Optional[List[str]] = None,
    deploy_name: Optional[str] = "Main",
) -> bool:
    if not (rg_name and isinstance(rg_name, str)):
        TypeError("'rg_name' parameter expected as string")
    if not (template_path and isinstance(template_path, str)):
        TypeError("'template_path' parameter expected as string")
    if isinstance(parameters, type(None)):
        parameters = []
    # if not isinstance(parameters, str): TypeError("'parameters' parameter expected as string")
    if not sh.is_list_of_strings(parameters):
        TypeError("'parameters' parameter expected as list of strings")
    if not (deploy_name and isinstance(deploy_name, str)):
        TypeError("'deploy_name' parameter expected as string")
    command: List[str] = [
        "az",
        "deployment",
        "group",
        "create",
        "--name={0}".format(deploy_name),
        "--resource-group={0}".format(rg_name),
        "--template-file={0}".format(template_path),
        # "--parameters={0}".format(parameters)
    ]
    if parameters:
        command.append("--parameters")
        command.extend(parameters)
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return rc == 0


# # Certificate method ended up more trouble with no gain compared to letting service principal make its own passphrase
# # Using certificate is viable but still need to fix 'openssl' conversion in 'key_vault_secret_download'
# # - certificate results in 2 secrets (certificate, passphrase) while username/passphrase has 1
# def login_strategy_certificate(subscription, cert_path, tenant, key_vault):
#     if not (subscription and isinstance(subscription, str)):
#         TypeError("login_strategy() expects 'subscription' parameter as string")
#     cert_path = sh.path_expand(cert_path)
#     secret_key = format_resource(sh.path_filename(cert_path))
#     # Check if account subscription exists
#     _log.debug("checking if already signed-in...")
#     account_info = account_get(subscription)

#     if not account_info:
#         if cert_path and tenant and sh.path_exists(cert_path, "f"):
#             _log.debug("not signed-in, attempting login with certificate...")
#             account_info = account_login(secret_key, cert_path, tenant)
#             if not account_info:
#                 _log.error("Azure certificate login failed, exiting...")
#                 sh.file_backup(cert_path)
#                 login_strategy(subscription, cert_path, tenant, key_vault)
#         else:
#             # Calling 'az login' in script works but prompt caused display issues within subprocess
#             _log.error("not signed-in, enter 'az login' to manually login before repeating your previous command")
#             sh.process_fail()

#     # Second parse attempt; last chance to be signed-in
#     if account_info:
#         _log.debug("signed-in, gathering account info...")
#         _account_parse(account_info)
#     else:
#         _log.error("Azure login failed, exiting...")
#         sh.process_fail()

#     # Ensure subscription is currently active
#     if not _az.subscription_is_default:
#         _log.debug("activating the selected subscription...")
#         account_active = account_set(subscription)
#         if not account_active:
#             _log.error("failed to activate subscription")
#             sh.process_fail()

#     # Ensure local certificate file exists
#     if not sh.path_exists(cert_path, "f"):
#         _log.debug("checking key vault for certificate...")
#         # key_vault_secret = key_vault_secret_get(key_vault, secret_key)
#         # if key_vault_secret: certificate = key_vault_secret.value
#         key_vault_secret_download(cert_path, key_vault, secret_key)

#         # if certificate:
#         if sh.path_exists(cert_path, "f"):
#             _log.debug("certificate successfully found in key vault!")
#             # _log.debug("certificate: {0}".format(certificate))
#         else:
#             _log.error("creating certificate and storing in key vault...")
#             cert_created = service_principal_rbac_set(secret_key, key_vault)
#             if cert_created:
#                 _log.info("certificate successfully created in key vault!")
#                 # certificate = key_vault_secret_get(key_vault, secret_key)

#                 # key_vault_secret = key_vault_secret_get(key_vault, secret_key)
#                 # if key_vault_secret: certificate = key_vault_secret.value
#                 key_vault_secret_download(cert_path, key_vault, secret_key)
#             else:
#                 _log.error("failed to create certificate")
#                 sh.process_fail()

#         # if certificate:
#         if sh.path_exists(cert_path, "f"):
#             # _log.debug("creating local certificate...")
#             # # Create PEM file from key vault secret and pass to next login
#             # sh.file_write(cert_path, certificate)
#             _log.info("local certificate successfully created!")
#             # Logout and confirm login with certificate file method
#             _log.debug("logging out and attempting login with certificate...")
#             account_logout()
#             # account_info = account_login(secret_key, cert_path, tenant)
#             # if not account_info:
#             #     _log.error("Azure certificate login failed, exiting...")
#             #     current_time = time.strftime("%Y%m%d-%H%M%S")
#             #     sh.file_rename(cert_path, "{0}.{1}.bak".format(cert_path, current_time))
#             #     sh.process_fail()
#             login_strategy(subscription, cert_path, tenant, key_vault)
#         else:
#             _log.error("failed to get certificate from key vault")
#             sh.process_fail()

#     _log.debug("login strategy successful!")
#     _log.debug("account_info: {0}".format(account_info))
#     return account_info


# ------------------------ Main Program ------------------------

# Initialize the logger
basename: str = "azure_boilerplate"
args = log.LogArgs()  # for external modules
_log: log._logger_type = log.get_logger(basename)

if __name__ == "__main__":
    # Returns argparse.Namespace; to pass into function, use **vars(self.args)
    def parse_arguments():
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        return parser.parse_args()

    args = parse_arguments()

    #  Configure the main logger
    log_handlers: List[log.LogHandlerOptions] = log.gen_basic_handlers(
        args.debug, args.log_path
    )
    log.set_handlers(_log, log_handlers)
    if args.debug:
        # Configure the shell_boilerplate logger
        _sh_log = log.get_logger("shell_boilerplate")
        log.set_handlers(_sh_log, log_handlers)
        sh.args.debug = args.debug

    _log.debug("args: {0}".format(args))
    _log.debug("------------------------------------------------")

    # --- Usage Example ---
    # python ~/.local/lib/python2.7/site-packages/azure_boilerplate.py --debug
    # python ~/.local/lib/python3.6/site-packages/azure_boilerplate.py --debug
