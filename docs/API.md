# API Documentation

## Base URL
`/api/v1`

## Endpoints

### Authentication
- `POST /auth/register`: Register a new user
- `POST /auth/login`: Authenticate user and return JWT
- `GET /auth/me`: Get current user details

### Projects
- `GET /projects`: List all projects for the user
- `POST /projects`: Create a new project
- `GET /projects/{id}`: Get project details
- `DELETE /projects/{id}`: Delete a project

### Datasets
- `POST /projects/{id}/datasets/upload`: Upload CSV dataset
- `GET /projects/{id}/datasets`: List datasets

### Forecasting
- `POST /projects/{id}/forecast/train`: Train Random Forest model (async)
- `GET /projects/{id}/forecast/status/{task_id}`: Check training status
- `POST /projects/{id}/forecast/predict`: Get N-day forecast

### Optimization
- `POST /projects/{id}/optimize/classical`: Run OR-Tools (async)
- `POST /projects/{id}/optimize/quantum`: Run QAOA (async)
- `GET /projects/{id}/optimize/runs`: List all optimization runs

### Validation
- `POST /projects/{id}/validate/queue`: Run Erlang C validation
- `GET /projects/{id}/validate/results`: Get validation results

### Reports
- `POST /projects/{id}/reports/generate`: Generate text report
- `GET /projects/{id}/reports`: List reports
- `GET /projects/{id}/reports/{id}/download`: Download report file
