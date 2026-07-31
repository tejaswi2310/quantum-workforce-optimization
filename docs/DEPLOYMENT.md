# Deployment Guide

This project is fully containerized using Docker and Docker Compose.

## Prerequisites
- Docker (v24+)
- Docker Compose (v2+)

## Local Development
To run the full stack locally:
```bash
cp .env.example .env
docker compose up --build -d
```
Access the application at `http://localhost`.

## Production Deployment (AWS ECS)
1. Build and push the Docker images (frontend, backend, ml-worker) to Amazon ECR.
2. Deploy the PostgreSQL database via Amazon RDS.
3. Deploy Redis using Amazon ElastiCache.
4. Create an ECS Cluster and define Task Definitions for the backend and ml-worker.
5. Host the frontend static files on S3 and serve them via CloudFront.
6. Ensure VPC Security Groups allow communication between ECS, RDS, and ElastiCache.
