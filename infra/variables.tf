variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "project_name" {
  type    = string
  default = "padelflow"
}

variable "db_name" {
  type = string
}

variable "db_user" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "my_ip" {
  type        = string
  description = "Your public IP for SSH access (x.x.x.x/32)"
}

variable "ssh_key_name" {
  type        = string
  description = "Existing AWS key pair name"
}