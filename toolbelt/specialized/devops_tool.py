"""DevOps Tool for Stack 3.0.
Provides templates and generation logic for cloud, container, and CI/CD configurations.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from ..tools.base import BaseTool, ToolResult

class DevOpsTool(BaseTool):
    """Tool for generating DevOps and Cloud infrastructure templates."""

    name = "devops_tool"
    description = "Provides templates for K8s, Docker, AWS, GCP, and CI/CD pipelines."
    category = "Infrastructure"

    # Cloud provider templates migrated from Stack 2.9
    CLOUD_TEMPLATES = {
        "aws": {
            "ec2": {
                "description": "AWS EC2 instance",
                "template": """# AWS EC2 Instance
resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name = "Stack3.0-App"
  }
}""",
            },
            "s3": {
                "description": "AWS S3 bucket",
                "template": """# AWS S3 Bucket
resource "aws_s3_bucket" "data_store" {
  bucket = "stack30-data-store"

  tags = {
    Name        = "Stack3.0 Data"
    Environment = "production"
  }
}""",
            },
            "lambda": {
                "description": "AWS Lambda function",
                "template": """# AWS Lambda Function
resource "aws_lambda_function" "handler" {
  filename         = "handler.zip"
  function_name    = "stack30_handler"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  source_code_hash = filebase64sha256("handler.zip")

  runtime = "python3.9"
}""",
            },
        },
        "gcp": {
            "compute": {
                "description": "GCP Compute Engine",
                "template": """# GCP Compute Engine
resource "google_compute_instance" "vm_instance" {
  name         = "stack30-vm"
  machine_type = "e2-micro"
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = "default"
  }
}""",
            },
            "storage": {
                "description": "GCP Cloud Storage",
                "template": """# GCP Cloud Storage
resource "google_storage_bucket" "bucket" {
  name          = "stack30-bucket"
  location      = "US"
  force_destroy = false

  labels = {
    environment = "production"
  }
}""",
            },
        },
        "docker": {
            "container": {
                "description": "Docker container configuration",
                "template": """# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run application
CMD ["python", "main.py"]""",
            },
            "compose": {
                "description": "Docker Compose configuration",
                "template": """# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://db:5432/app
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=app
      - POSTGRES_PASSWORD=secret

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
""",
            },
        },
        "kubernetes": {
            "deployment": {
                "description": "Kubernetes Deployment",
                "template": """# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stack30-app
  labels:
    app: stack30
spec:
  replicas: 3
  selector:
    matchLabels:
      app: stack30
  template:
    metadata:
      labels:
        app: stack30
    spec:
      containers:
      - name: app
        image: stack30:latest
        ports:
        - containerPort: 8000
        resources:
          limits:
            cpu: "500m"
            memory: "256Mi"
""",
            },
            "service": {
                "description": "Kubernetes Service",
                "template": """# k8s-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: stack30-service
spec:
  selector:
    app: stack30
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
""",
            },
        },
    }

    CICD_TEMPLATES = {
        "github_actions": {
            "description": "GitHub Actions workflow",
            "template": """# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      run: |
        pytest tests/

    - name: Lint
      run: |
        ruff check .
""",
        },
        "gitlab_ci": {
            "description": "GitLab CI pipeline",
            "template": """# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pytest tests/
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

build:
  stage: build
  script:
    - docker build -t stack30:$CI_COMMIT_SHA .
  rules:
    - if: $CI_COMMIT_BRANCH == "main"

deploy:
  stage: deploy
  script:
    - kubectl apply -f k8s/
  environment:
    name: production
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
""",
        },
    }

    TERRAFORM_VARIABLES = {
        "description": "Terraform variables",
        "template": """# variables.tf
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}
""",
    }

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_cloud_template", "get_cicd_template", "list_templates", "generate_k8s", "generate_dockerfile", "parse_compose"],
                    "description": "The DevOps action to perform"
                },
                "provider": {"type": "string", "description": "Cloud provider (aws, gcp, docker, kubernetes)"},
                "service": {"type": "string", "description": "Cloud service name"},
                "platform": {"type": "string", "description": "CI/CD platform (github_actions, gitlab_ci)"},
                "app_name": {"type": "string", "description": "Application name for K8s manifest"},
                "image": {"type": "string", "description": "Container image for K8s manifest"},
                "replicas": {"type": "integer", "default": 3},
                "port": {"type": "integer", "default": 8000},
                "language": {"type": "string", "default": "python"},
                "version": {"type": "string", "default": "3.11"},
                "compose_content": {"type": "string", "description": "Docker compose YAML content to parse"}
            },
            "required": ["action"]
        }

    def execute(self, input_data: Dict[str, Any]) -> ToolResult[Any]:
        action = input_data.get("action")

        if action == "get_cloud_template":
            provider = input_data.get("provider")
            service = input_data.get("service")
            template = self.CLOUD_TEMPLATES.get(provider, {}).get(service, {}).get("template")
            return ToolResult(data=template if template else "Template not found")

        elif action == "get_cicd_template":
            platform = input_data.get("platform")
            template = self.CICD_TEMPLATES.get(platform, {}).get("template")
            return ToolResult(data=template if template else "Template not found")

        elif action == "list_templates":
            return ToolResult(data={
                "cloud_providers": list(self.CLOUD_TEMPLATES.keys()),
                "cicd": list(self.CICD_TEMPLATES.keys()),
            })

        elif action == "generate_k8s":
            app_name = input_data.get("app_name", "stack30-app")
            image = input_data.get("image", "stack30:latest")
            replicas = input_data.get("replicas", 3)
            port = input_data.get("port", 8000)
            manifest = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  labels:
    app: {app_name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
      - name: {app_name}
        image: {image}
        ports:
        - containerPort: {port}
        resources:
          limits:
            cpu: "1000m"
            memory: "512Mi"
          requests:
            cpu: "100m"
            memory: "128Mi"
---

apiVersion: v1
kind: Service
metadata:
  name: {app_name}-service
spec:
  selector:
    app: {app_name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: {port}
  type: LoadBalancer
"""
            return ToolResult(data=manifest)

        elif action == "generate_dockerfile":
            language = input_data.get("language", "python")
            version = input_data.get("version", "3.11")
            port = input_data.get("port", 8000)
            base_images = {
                "python": f"python:{version}-slim",
                "node": f"node:{version}-slim",
                "go": f"golang:{version}",
                "rust": f"rust:{version}-slim",
            }
            base = base_images.get(language, f"python:{version}-slim")
            dockerfile = f"""FROM {base}

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE {port}

# Run application
CMD ["python", "main.py"]
"""
            return ToolResult(data=dockerfile)

        elif action == "parse_compose":
            content = input_data.get("compose_content", "")
            services = re.findall(r'^  (\w+):$', content, re.MULTILINE)
            return ToolResult(data={"services": services, "count": len(services)})

        return ToolResult(success=False, error=f"Unsupported action: {action}")
