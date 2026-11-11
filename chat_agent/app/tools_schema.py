"""
OpenAPI/Function tool schemas for available GET APIs across AmNonOvens and Fabrico360-BE.
"""

TOOLS_SCHEMA = [
    # ------------------ UNITS OF MEASURE (UOM) ------------------
    {
        "type": "function",
        "function": {
            "name": "get_uom_list",
            "description": "Fetch configured Units of Measure (UOM) master records, units (Roll, CM, Meters, Pieces, Box, Unit, Kgs, Nos, etc.), and descriptions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "uom_name": {
                        "type": "string",
                        "description": "Optional Unit of Measure name to filter (e.g., Roll, Meters, Pieces, Box, Unit, CM)."
                    }
                }
            }
        }
    },

    # ------------------ INVENTORY & WAREHOUSE ------------------
    {
        "type": "function",
        "function": {
            "name": "get_inventory_stock",
            "description": "Fetch inventory stock balances, current available quantities, SKU details, batches, and locations from the inventory registry. Use when inquiring about stock balances, inventory levels, ROQL (Reorder Quantity Level), warehouse locations, or comparing stock vs threshold for a product/SKU. DO NOT call get_products alongside get_inventory_stock for the same SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Optional Product ID to filter inventory stock."
                    },
                    "sku_id": {
                        "type": "string",
                        "description": "Optional SKU Code or product code."
                    },
                    "location_id": {
                        "type": "integer",
                        "description": "Optional Store / Warehouse location ID."
                    },
                    "search": {
                        "type": "string",
                        "description": "Free text search for product name, SKU, or batch."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_store_locations",
            "description": "Fetch warehouse store locations, sub-locations, and racks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "Optional location or room name."
                    }
                }
            }
        }
    },

    # ------------------ PRODUCTS & MASTER CONFIG ------------------
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "Retrieve registered products, catalog specifications, categories, and units of measure (UOM). Use ONLY when general catalog details, specifications, or item metadata are requested and current inventory stock levels are NOT needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Product name or search keyword."
                    },
                    "product_group_id": {
                        "type": "integer",
                        "description": "Optional Product group / category ID."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_variants",
            "description": "Retrieve product variants, style configurations, and dynamic variant attributes (e.g. Dimensions, GSM, Width, Color, Size).",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Product ID to inspect variants for."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_groups",
            "description": "Retrieve list of product groups, material categories, and classifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Optional name of the product group."
                    }
                }
            }
        }
    },

    # ------------------ BILL OF MATERIALS & COSTING ------------------
    {
        "type": "function",
        "function": {
            "name": "get_bill_of_materials",
            "description": "Retrieve Bill of Materials (BOM) master details, required raw material components, and standard consumption metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Product ID to inspect BOM for."
                    },
                    "bom_code": {
                        "type": "string",
                        "description": "Specific BOM code or reference."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cost_estimations",
            "description": "Fetch cost estimations, raw material costs, operational expenses, and calculated product costs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Optional Product ID."
                    },
                    "estimate_no": {
                        "type": "string",
                        "description": "Optional Cost estimation number or reference."
                    }
                }
            }
        }
    },

    # ------------------ SALES & CUSTOMER ORDERS ------------------
    {
        "type": "function",
        "function": {
            "name": "get_customer_purchase_orders",
            "description": "Fetch customer purchase orders (CPO), order status, order quantities, delivery dates, and customer details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_no": {
                        "type": "string",
                        "description": "Optional customer PO / order number."
                    },
                    "customer_id": {
                        "type": "integer",
                        "description": "Optional Customer ID."
                    },
                    "status": {
                        "type": "string",
                        "description": "Order status filter (e.g. Approved, Pending, In Production)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_pipeline",
            "description": "Fetch sales pipeline leads, prospective deals, deal values, and stage progression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {
                        "type": "string",
                        "description": "Optional sales stage filter."
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Customer or prospective lead name."
                    }
                }
            }
        }
    },

    # ------------------ VENDORS & SUPPLIERS ------------------
    {
        "type": "function",
        "function": {
            "name": "get_vendors",
            "description": "Fetch registered suppliers, vendor directory, contact details, and supplier codes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_name": {
                        "type": "string",
                        "description": "Optional vendor or supplier name to search."
                    },
                    "city": {
                        "type": "string",
                        "description": "City location filter."
                    }
                }
            }
        }
    },

    # ------------------ CUSTOMERS & CLIENT DIRECTORY ------------------
    {
        "type": "function",
        "function": {
            "name": "get_customers",
            "description": "Fetch registered customer directory, client accounts, contact persons, GST numbers, and addresses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Optional customer or company name to search (e.g., TechGenzi, Madura Coats, DemoCustomerOne)."
                    },
                    "city": {
                        "type": "string",
                        "description": "City location filter."
                    }
                }
            }
        }
    },

    # ------------------ PRODUCTION & PLANNING ------------------
    {
        "type": "function",
        "function": {
            "name": "get_job_orders",
            "description": "Retrieve production Job Orders, work order numbers, target quantities, progress status, and dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_order_no": {
                        "type": "string",
                        "description": "Job order number."
                    },
                    "status": {
                        "type": "string",
                        "description": "Job order status (e.g. Running, Completed, Planned)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_production_plans",
            "description": "Retrieve daily/weekly production plans, target assembly lines, schedules, and planned production quantities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_date": {
                        "type": "string",
                        "description": "Date of the plan (YYYY-MM-DD)."
                    },
                    "line_id": {
                        "type": "integer",
                        "description": "Optional Assembly line ID."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_production_execution_logs",
            "description": "Retrieve real-time hourly and daily production logs, output quantities, and defect counts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Production date (YYYY-MM-DD)."
                    },
                    "job_order_id": {
                        "type": "integer",
                        "description": "Optional Job order ID."
                    }
                }
            }
        }
    },

    # ------------------ GRN, QC & DISPATCH ------------------
    {
        "type": "function",
        "function": {
            "name": "get_grn_qc_records",
            "description": "Fetch Goods Receipt Notes (GRN), inbound raw material inspection reports, and Quality Check (QC) status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "grn_number": {
                        "type": "string",
                        "description": "Optional GRN number."
                    },
                    "qc_status": {
                        "type": "string",
                        "description": "QC status filter (e.g. Accepted, Rejected, Pending)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_qc_rejection_report",
            "description": "Fetch quality inspection defect logs, rework rates, fabric scrap %, and quality failure causes across lines or orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style_id": {
                        "type": "integer",
                        "description": "Optional Style ID."
                    },
                    "stage_id": {
                        "type": "integer",
                        "description": "Optional Stage ID."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dispatch_records",
            "description": "Retrieve goods dispatch entries, delivery challans (DC), dispatched product quantities, and vehicles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dc_number": {
                        "type": "string",
                        "description": "Delivery Challan number."
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Customer name."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dispatch_delivery_report",
            "description": "Retrieve customer delivery and dispatch reports including delivery challan (DC), customer invoice numbers, driver/vehicle details, and delivered vs ordered quantities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)."
                    },
                    "customer_purchase_id": {
                        "type": "integer",
                        "description": "Optional customer purchase order ID."
                    }
                }
            }
        }
    },

    # ------------------ SERVER AGGREGATIONS & HR ------------------
    {
        "type": "function",
        "function": {
            "name": "get_production_summary",
            "description": "Fetch consolidated plant-wide manufacturing dashboard, KPI rollups, floor-wise production output, WIP units, direct labour cost, and departmental overhead costs across active floors (B1, B2, B3, B5). Use for executive morning briefings and plant health inquiries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date for consolidated factory performance (YYYY-MM-DD)."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for consolidated factory performance (YYYY-MM-DD)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pending_summary",
            "description": "Fetch executive summary of pending production plans, delayed items, and floor backlogs.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_labour_costing",
            "description": "Fetch plan-wise and stage-wise actual vs estimated labour costs, completed output, and stage variance across Cutting, Stitching, Pouch Packing, and Box Packing to isolate margin leaks and cost overruns. Keep results_per_page small (5 to 10) to protect context window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date for labour cost audit (YYYY-MM-DD)."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for labour cost audit (YYYY-MM-DD)."
                    },
                    "results_per_page": {
                        "type": "integer",
                        "description": "Number of production plans to return (default 5, max 10 to prevent context overflow)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_attendance",
            "description": "Fetch daily shop-floor employee line attendance, shift status, and assigned workstations from line employee reports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Attendance date (YYYY-MM-DD). Defaults to current date."
                    },
                    "results_per_page": {
                        "type": "integer",
                        "description": "Number of records per page (default 15)."
                    }
                }
            }
        }
    }
]
