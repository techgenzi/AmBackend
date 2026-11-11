# API Documentation for Job Order Management

## Base URL
`/job_order/`

## Authentication
All endpoints require authentication via the `login_required` decorator.

---

## 1. Get List of Job Orders
### GET /
- **Description**: Retrieves a paginated list of Job Orders with optional filters.
- **Parameters**:
  - `current_user` (query): The current authenticated user object.
  - `paged` (query, optional): Page number for pagination (default: 1).
  - `results_per_page` (query, optional): Number of results per page (default: 0, all results).
  - `type`, `status`, `joborderno`, `vendorid`, `joborderid` (queries, optional): Filters.
- **Response**:
  ```json
  {
      "total_results": 100,
      "page": 1,
      "results_per_page": 10,
      "results": [
          {
              "joborderid": 1,
              "joborderno": "PO-000001",
              "vendorid": 5,
              "type": "purchase_order",
              "status": "approved",
              "created_on": "2024-06-01T12:34:56",
              ...
          },
          ...
      ]
  }

2. Create Job Order
POST /
Description: Creates a new Job Order and returns the inserted ID.
Parameters:
current_user (query): The current authenticated user object.
Request Body (JSON):
{
    "joborderproposalid": 10,
    "joborderno": "1098",
    "vendorid": 5,
    ...
}
Response:
{
    "result": {
        "joborderid": 1,
        "joborderno": "PO-000001",
        ...
    },
    "message": "Job order record has been created successfully",
    "primary_key": "joborderid"
}
3. Get Single Job Order
GET /<joborder_id>/
Description: Retrieves a single Job Order by ID.
Parameters:
current_user (query): The current authenticated user object.
joborder_id (path): ID of the Job Order to retrieve.
Response:
{
    "joborderid": 1,
    "joborderno": "PO-000001",
    "vendorid": 5,
    "type": "purchase_order",
    "status": "approved",
    "created_on": "2024-06-01T12:34:56",
    ...
}
4. Update Job Order
PUT /<joborder_id>/
Description: Updates an existing Job Order.
Parameters:
current_user (query): The current authenticated user object.
joborder_id (path): ID of the Job Order to update.
Request Body (JSON):
{
    "status": "completed",
    ...
}
Response:
{
    "result": {
        "joborderid": 1,
        "joborderno": "PO-000001",
        "status": "completed",
        ...
    },
    "message": "Job order record has been updated successfully"
}
5. Partially Update Job Order
PATCH /<joborder_id>/
Description: Partially updates an existing Job Order.
Parameters:
current_user (query): The current authenticated user object.
joborder_id (path): ID of the Job Order to update.
Request Body (JSON):
{
    "status": "in_progress",
    ...
}
Response:
{
    "result": {
        "joborderid": 1,
        "joborderno": "PO-000001",
        "status": "in_progress",
        ...
    },
    "message": "Job order record has been partially updated"
}
6. Delete Job Order
DELETE /<joborder_id>/
Description: Soft deletes a Job Order.
Parameters:
current_user (query): The current authenticated user object.
joborder_id (path): ID of the Job Order to delete.
Response:
{
    "message": "Job order record has been soft deleted"
}

7. Compare BOM and Purchase Order by SKU ID
GET /sku_id/
Description: Compares quantities of SKUs between Job Orders and Bills of Materials (BOM).
Parameters:
current_user (query): The current authenticated user object.
paged (query, optional): Page number for pagination (default: 1).
results_per_page (query, optional): Number of results per page (default: 0, all results).
sku_id (query, optional): SKU ID to compare quantities.
Response:
{
    "po": [
        {"sku_id": "SKU001", "quantity": 50},
        {"sku_id": "SKU002", "quantity": 30},
        ...
    ],
    "bom": [
        {"sku_id": "SKU001", "quantity": 55},
        {"sku_id": "SKU003", "quantity": 25},
        ...
    ]
}
8. Create Job Quote
POST /Quote/
Description: Creates a new Job Quote and returns the inserted ID.
Parameters:
current_user (query): The current authenticated user object.
Request Body (JSON):
{
    "joborderproposalid": 10,
    "joborderno": "Q-1098",
    "vendorid": 5,
    ...
}
Response:
{
    "result": {
        "joborderid": 1,
        "joborderno": "Q-000001",
        ...
    },
    "message": "Job quote record has been created successfully",
    "primary_key": "joborderid"
}