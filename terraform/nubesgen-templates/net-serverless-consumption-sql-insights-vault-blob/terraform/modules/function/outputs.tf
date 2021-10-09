output "application_hostname" {
  value       = "https://${azurerm_function_app.application.default_hostname}"
  description = "The Azure Functions application URL."
}

output "application_caf_name" {
  value       = azurecaf_name.function_app.result
  description = "The application name generated by the Azure Cloud Adoption Framework."
}