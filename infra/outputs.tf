output "api_public_ip" {
  value = aws_instance.api.public_ip
}

output "db_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "db_name" {
  value = aws_db_instance.postgres.db_name
}
