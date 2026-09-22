# API Contracts

This document is automatically generated from the live FastAPI OpenAPI specification.
It defines the authoritative API contracts for all endpoints.

## capacity

### GET /api/v1/centres/{id}/capacity

**Purpose:** Get Centre Capacity

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
- crop_id (string, format: uuid, required) — Crop Id
- date (string, format: date, required) — Date

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "active": {
      "title": "Active",
      "type": "boolean"
    },
    "allocated_quantity_kg": {
      "title": "Allocated Quantity Kg",
      "type": "string"
    },
    "available_capacity_kg": {
      "title": "Available Capacity Kg",
      "type": "string"
    },
    "capacity_status": {
      "enum": [
        "INACTIVE",
        "AVAILABLE",
        "PARTIAL",
        "FULL"
      ],
      "title": "CapacityStatus",
      "type": "string"
    },
    "centre_id": {
      "format": "uuid",
      "title": "Centre Id",
      "type": "string"
    },
    "crop_id": {
      "format": "uuid",
      "title": "Crop Id",
      "type": "string"
    },
    "date": {
      "format": "date",
      "title": "Date",
      "type": "string"
    },
    "procured_quantity_kg": {
      "title": "Procured Quantity Kg",
      "type": "string"
    },
    "total_capacity_kg": {
      "title": "Total Capacity Kg",
      "type": "string"
    },
    "utilisation": {
      "title": "Utilisation",
      "type": "string"
    }
  },
  "required": [
    "centre_id",
    "crop_id",
    "date",
    "total_capacity_kg",
    "allocated_quantity_kg",
    "procured_quantity_kg",
    "available_capacity_kg",
    "utilisation",
    "capacity_status",
    "active"
  ],
  "title": "CapacityRecordResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

## centres

### GET /api/v1/centres

**Purpose:** List Centres

**Authentication:** required

**Path parameters:**
`none`

**Query parameters:**
- page (integer, optional) — Page
- page_size (integer, optional) — Page Size

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "items": {
      "items": {
        "properties": {
          "active": {
            "default": true,
            "title": "Active",
            "type": "boolean"
          },
          "block": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Block"
          },
          "counters": {
            "items": {
              "properties": {
                "active": {
                  "default": true,
                  "title": "Active",
                  "type": "boolean"
                },
                "centre_id": {
                  "format": "uuid",
                  "title": "Centre Id",
                  "type": "string"
                },
                "created_at": {
                  "format": "date-time",
                  "title": "Created At",
                  "type": "string"
                },
                "id": {
                  "format": "uuid",
                  "title": "Id",
                  "type": "string"
                },
                "name": {
                  "title": "Name",
                  "type": "string"
                },
                "updated_at": {
                  "format": "date-time",
                  "title": "Updated At",
                  "type": "string"
                }
              },
              "required": [
                "id",
                "centre_id",
                "name",
                "created_at",
                "updated_at"
              ],
              "title": "CounterResponse",
              "type": "object"
            },
            "title": "Counters",
            "type": "array"
          },
          "created_at": {
            "format": "date-time",
            "title": "Created At",
            "type": "string"
          },
          "district": {
            "title": "District",
            "type": "string"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "latitude": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Latitude"
          },
          "longitude": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "title": "Longitude"
          },
          "name": {
            "title": "Name",
            "type": "string"
          },
          "state": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "State"
          },
          "updated_at": {
            "format": "date-time",
            "title": "Updated At",
            "type": "string"
          }
        },
        "required": [
          "id",
          "created_at",
          "name",
          "district",
          "updated_at"
        ],
        "title": "CentreResponse",
        "type": "object"
      },
      "title": "Items",
      "type": "array"
    },
    "page": {
      "title": "Page",
      "type": "integer"
    },
    "page_size": {
      "title": "Page Size",
      "type": "integer"
    },
    "total": {
      "title": "Total",
      "type": "integer"
    }
  },
  "required": [
    "items",
    "page",
    "page_size",
    "total"
  ],
  "title": "PaginationResponse[CentreResponse]",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### GET /api/v1/centres/{centre_id}/allocation

**Purpose:** Get Centre Allocations

**Authentication:** required

**Path parameters:**
- centre_id (string, format: uuid) — Centre Id

**Query parameters:**
- allocation_date (string, format: date | null, optional) — Allocation Date
- crop_id (string, format: uuid | null, optional) — Crop Id

**Request body:**
`none`

**Response 200:**
```json
{
  "items": {
    "properties": {
      "allocated_quantity_kg": {
        "title": "Allocated Quantity Kg",
        "type": "string"
      },
      "allocation_run_id": {
        "format": "uuid",
        "title": "Allocation Run Id",
        "type": "string"
      },
      "created_at": {
        "format": "date-time",
        "title": "Created At",
        "type": "string"
      },
      "farmer_id": {
        "format": "uuid",
        "title": "Farmer Id",
        "type": "string"
      },
      "id": {
        "format": "uuid",
        "title": "Id",
        "type": "string"
      },
      "intent_id": {
        "format": "uuid",
        "title": "Intent Id",
        "type": "string"
      },
      "ordering_reason": {
        "title": "Ordering Reason",
        "type": "string"
      },
      "rank": {
        "title": "Rank",
        "type": "integer"
      },
      "remaining_capacity_kg": {
        "title": "Remaining Capacity Kg",
        "type": "string"
      },
      "requested_quantity_kg": {
        "title": "Requested Quantity Kg",
        "type": "string"
      },
      "selected": {
        "title": "Selected",
        "type": "boolean"
      },
      "tie_break_digest": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "type": "null"
          }
        ],
        "title": "Tie Break Digest"
      }
    },
    "required": [
      "id",
      "allocation_run_id",
      "intent_id",
      "farmer_id",
      "requested_quantity_kg",
      "allocated_quantity_kg",
      "remaining_capacity_kg",
      "selected",
      "rank",
      "ordering_reason",
      "created_at"
    ],
    "title": "AllocationDecisionResponse",
    "type": "object"
  },
  "title": "Response Get Centre Allocations Api V1 Centres  Centre Id  Allocation Get",
  "type": "array"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### GET /api/v1/centres/{id}

**Purpose:** Get Centre

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "active": {
      "default": true,
      "title": "Active",
      "type": "boolean"
    },
    "block": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Block"
    },
    "counters": {
      "items": {
        "properties": {
          "active": {
            "default": true,
            "title": "Active",
            "type": "boolean"
          },
          "centre_id": {
            "format": "uuid",
            "title": "Centre Id",
            "type": "string"
          },
          "created_at": {
            "format": "date-time",
            "title": "Created At",
            "type": "string"
          },
          "id": {
            "format": "uuid",
            "title": "Id",
            "type": "string"
          },
          "name": {
            "title": "Name",
            "type": "string"
          },
          "updated_at": {
            "format": "date-time",
            "title": "Updated At",
            "type": "string"
          }
        },
        "required": [
          "id",
          "centre_id",
          "name",
          "created_at",
          "updated_at"
        ],
        "title": "CounterResponse",
        "type": "object"
      },
      "title": "Counters",
      "type": "array"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "district": {
      "title": "District",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "latitude": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "title": "Latitude"
    },
    "longitude": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "title": "Longitude"
    },
    "name": {
      "title": "Name",
      "type": "string"
    },
    "state": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "State"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "created_at",
    "name",
    "district",
    "updated_at"
  ],
  "title": "CentreResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

## farmers

### POST /api/v1/farmers

**Purpose:** Create Farmer

**Authentication:** required

**Path parameters:**
`none`

**Query parameters:**
`none`

**Request body:**
```json
{
  "properties": {
    "block": {
      "anyOf": [
        {
          "maxLength": 120,
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Block"
    },
    "district": {
      "anyOf": [
        {
          "maxLength": 120,
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "District"
    },
    "farmer_id": {
      "maxLength": 64,
      "minLength": 1,
      "title": "Farmer Id",
      "type": "string"
    },
    "name": {
      "maxLength": 120,
      "minLength": 1,
      "title": "Name",
      "type": "string"
    },
    "phone": {
      "anyOf": [
        {
          "pattern": "^\\d{10}$",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Phone"
    },
    "state": {
      "anyOf": [
        {
          "maxLength": 120,
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "State"
    },
    "village": {
      "anyOf": [
        {
          "maxLength": 120,
          "minLength": 1,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Village"
    }
  },
  "required": [
    "farmer_id",
    "name"
  ],
  "title": "FarmerCreate",
  "type": "object"
}
```

**Response 201:**
```json
{
  "properties": {
    "active": {
      "default": true,
      "title": "Active",
      "type": "boolean"
    },
    "block": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Block"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "district": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "District"
    },
    "farmer_id": {
      "maxLength": 64,
      "minLength": 1,
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "name": {
      "title": "Name",
      "type": "string"
    },
    "phone": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Phone"
    },
    "state": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "State"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    },
    "village": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Village"
    }
  },
  "required": [
    "id",
    "created_at",
    "farmer_id",
    "name",
    "updated_at"
  ],
  "title": "FarmerResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### POST /api/v1/farmers/me/centre-selection

**Purpose:** Select Priority Centre

**Authentication:** required

**Path parameters:**
`none`

**Query parameters:**
`none`

**Request body:**
```json
{
  "additionalProperties": false,
  "properties": {
    "crop_id": {
      "format": "uuid",
      "title": "Crop Id",
      "type": "string"
    },
    "preferred_centres": {
      "description": "At least one centre preference is required",
      "items": {
        "properties": {
          "centre_id": {
            "format": "uuid",
            "title": "Centre Id",
            "type": "string"
          },
          "priority": {
            "description": "Priority starting at 1",
            "minimum": 1.0,
            "title": "Priority",
            "type": "integer"
          }
        },
        "required": [
          "centre_id",
          "priority"
        ],
        "title": "CentrePreference",
        "type": "object"
      },
      "minItems": 1,
      "title": "Preferred Centres",
      "type": "array"
    },
    "ready_date": {
      "format": "date",
      "title": "Ready Date",
      "type": "string"
    },
    "requested_quantity_kg": {
      "anyOf": [
        {
          "exclusiveMinimum": 0.0,
          "type": "number"
        },
        {
          "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
          "type": "string"
        }
      ],
      "description": "Requested quantity must be positive",
      "title": "Requested Quantity Kg"
    }
  },
  "required": [
    "crop_id",
    "ready_date",
    "requested_quantity_kg",
    "preferred_centres"
  ],
  "title": "PriorityCentreSelectionRequest",
  "type": "object"
}
```

**Response 200:**
```json
{
  "properties": {
    "available_capacity_kg": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Available Capacity Kg"
    },
    "crop_id": {
      "format": "uuid",
      "title": "Crop Id",
      "type": "string"
    },
    "evaluated_centres": {
      "items": {
        "properties": {
          "centre_id": {
            "format": "uuid",
            "title": "Centre Id",
            "type": "string"
          },
          "priority": {
            "title": "Priority",
            "type": "integer"
          },
          "reason": {
            "title": "Reason",
            "type": "string"
          },
          "status": {
            "title": "Status",
            "type": "string"
          }
        },
        "required": [
          "centre_id",
          "priority",
          "status",
          "reason"
        ],
        "title": "CentreEvaluationDetail",
        "type": "object"
      },
      "title": "Evaluated Centres",
      "type": "array"
    },
    "message": {
      "title": "Message",
      "type": "string"
    },
    "ready_date": {
      "format": "date",
      "title": "Ready Date",
      "type": "string"
    },
    "requested_quantity_kg": {
      "title": "Requested Quantity Kg",
      "type": "string"
    },
    "selected_centre_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Selected Centre Id"
    },
    "selected_priority": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "title": "Selected Priority"
    },
    "success": {
      "title": "Success",
      "type": "boolean"
    }
  },
  "required": [
    "success",
    "crop_id",
    "ready_date",
    "requested_quantity_kg",
    "evaluated_centres",
    "message"
  ],
  "title": "PriorityCentreSelectionResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### GET /api/v1/farmers/me/intents/{intent_id}/allocation

**Purpose:** Get Farmer Intent Allocation

**Authentication:** required

**Path parameters:**
- intent_id (string, format: uuid) — Intent Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "allocated_quantity_kg": {
      "title": "Allocated Quantity Kg",
      "type": "string"
    },
    "allocation_run_id": {
      "format": "uuid",
      "title": "Allocation Run Id",
      "type": "string"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "intent_id": {
      "format": "uuid",
      "title": "Intent Id",
      "type": "string"
    },
    "ordering_reason": {
      "title": "Ordering Reason",
      "type": "string"
    },
    "rank": {
      "title": "Rank",
      "type": "integer"
    },
    "remaining_capacity_kg": {
      "title": "Remaining Capacity Kg",
      "type": "string"
    },
    "requested_quantity_kg": {
      "title": "Requested Quantity Kg",
      "type": "string"
    },
    "selected": {
      "title": "Selected",
      "type": "boolean"
    },
    "tie_break_digest": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Tie Break Digest"
    }
  },
  "required": [
    "id",
    "allocation_run_id",
    "intent_id",
    "farmer_id",
    "requested_quantity_kg",
    "allocated_quantity_kg",
    "remaining_capacity_kg",
    "selected",
    "rank",
    "ordering_reason",
    "created_at"
  ],
  "title": "AllocationDecisionResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### GET /api/v1/farmers/{id}

**Purpose:** Get Farmer

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "active": {
      "default": true,
      "title": "Active",
      "type": "boolean"
    },
    "block": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Block"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "district": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "District"
    },
    "farmer_id": {
      "maxLength": 64,
      "minLength": 1,
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "name": {
      "title": "Name",
      "type": "string"
    },
    "phone": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Phone"
    },
    "state": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "State"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    },
    "village": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Village"
    }
  },
  "required": [
    "id",
    "created_at",
    "farmer_id",
    "name",
    "updated_at"
  ],
  "title": "FarmerResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

## Health

### GET /api/v1/health

**Purpose:** Health

**Authentication:** public

**Path parameters:**
`none`

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "additionalProperties": {
    "type": "string"
  },
  "title": "Response Health Api V1 Health Get",
  "type": "object"
}
```

### GET /api/v1/ready

**Purpose:** Ready

**Authentication:** public

**Path parameters:**
`none`

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "additionalProperties": {
    "type": "string"
  },
  "title": "Response Ready Api V1 Ready Get",
  "type": "object"
}
```

## procurement

### POST /api/v1/procurement

**Purpose:** Create Procurement

**Authentication:** required

**Path parameters:**
`none`

**Query parameters:**
`none`

**Request body:**
```json
{
  "properties": {
    "centre_id": {
      "format": "uuid",
      "title": "Centre Id",
      "type": "string"
    },
    "crop_id": {
      "format": "uuid",
      "title": "Crop Id",
      "type": "string"
    },
    "expected_quantity_kg": {
      "anyOf": [
        {
          "exclusiveMinimum": 0.0,
          "type": "number"
        },
        {
          "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
          "type": "string"
        }
      ],
      "title": "Expected Quantity Kg"
    },
    "farmer_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Farmer Id"
    },
    "land_holding_id": {
      "format": "uuid",
      "title": "Land Holding Id",
      "type": "string"
    },
    "ready_date": {
      "format": "date",
      "title": "Ready Date",
      "type": "string"
    }
  },
  "required": [
    "centre_id",
    "crop_id",
    "land_holding_id",
    "expected_quantity_kg",
    "ready_date"
  ],
  "title": "ProcurementIntentCreate",
  "type": "object"
}
```

**Response 201:**
```json
{
  "properties": {
    "cancellation_reason": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancellation Reason"
    },
    "centre_id": {
      "format": "uuid",
      "title": "Centre Id",
      "type": "string"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "created_by": {
      "format": "uuid",
      "title": "Created By",
      "type": "string"
    },
    "crop_id": {
      "format": "uuid",
      "title": "Crop Id",
      "type": "string"
    },
    "expected_quantity_kg": {
      "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
      "title": "Expected Quantity Kg",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "land_holding_id": {
      "format": "uuid",
      "title": "Land Holding Id",
      "type": "string"
    },
    "ready_date": {
      "format": "date",
      "title": "Ready Date",
      "type": "string"
    },
    "status": {
      "enum": [
        "PENDING",
        "APPROVED",
        "REJECTED",
        "CANCELLED",
        "COMPLETED"
      ],
      "title": "IntentStatus",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "farmer_id",
    "centre_id",
    "crop_id",
    "land_holding_id",
    "expected_quantity_kg",
    "ready_date",
    "status",
    "created_by",
    "created_at",
    "updated_at"
  ],
  "title": "ProcurementIntentResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### GET /api/v1/procurement/{id}

**Purpose:** Get Procurement Record

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "cancellation_reason": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancellation Reason"
    },
    "centre_id": {
      "format": "uuid",
      "title": "Centre Id",
      "type": "string"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "created_by": {
      "format": "uuid",
      "title": "Created By",
      "type": "string"
    },
    "crop_id": {
      "format": "uuid",
      "title": "Crop Id",
      "type": "string"
    },
    "expected_quantity_kg": {
      "pattern": "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$",
      "title": "Expected Quantity Kg",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "land_holding_id": {
      "format": "uuid",
      "title": "Land Holding Id",
      "type": "string"
    },
    "ready_date": {
      "format": "date",
      "title": "Ready Date",
      "type": "string"
    },
    "status": {
      "enum": [
        "PENDING",
        "APPROVED",
        "REJECTED",
        "CANCELLED",
        "COMPLETED"
      ],
      "title": "IntentStatus",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "farmer_id",
    "centre_id",
    "crop_id",
    "land_holding_id",
    "expected_quantity_kg",
    "ready_date",
    "status",
    "created_by",
    "created_at",
    "updated_at"
  ],
  "title": "ProcurementIntentResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

## queues

### GET /api/v1/queues/{id}

**Purpose:** Get Queue Status

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "centre_id": {
      "format": "uuid",
      "title": "Centre Id",
      "type": "string"
    },
    "current_called_token": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Current Called Token"
    },
    "date": {
      "format": "date",
      "title": "Date",
      "type": "string"
    },
    "last_issued_token": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Last Issued Token"
    },
    "queue_id": {
      "format": "uuid",
      "title": "Queue Id",
      "type": "string"
    },
    "status": {
      "enum": [
        "OPEN",
        "PAUSED",
        "CLOSED"
      ],
      "title": "QueueStatus",
      "type": "string"
    },
    "total_called": {
      "title": "Total Called",
      "type": "integer"
    },
    "total_cancelled": {
      "title": "Total Cancelled",
      "type": "integer"
    },
    "total_completed": {
      "title": "Total Completed",
      "type": "integer"
    },
    "total_processing": {
      "title": "Total Processing",
      "type": "integer"
    },
    "total_waiting": {
      "title": "Total Waiting",
      "type": "integer"
    }
  },
  "required": [
    "queue_id",
    "centre_id",
    "date",
    "status",
    "total_waiting",
    "total_called",
    "total_processing",
    "total_completed",
    "total_cancelled"
  ],
  "title": "QueueStatusResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### POST /api/v1/queues/{id}/call-next

**Purpose:** Call Next Token

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
```json
{
  "anyOf": [
    {
      "properties": {
        "counter_id": {
          "anyOf": [
            {
              "format": "uuid",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "description": "Optional counter ID calling the token",
          "title": "Counter Id"
        }
      },
      "title": "TokenCallNextRequest",
      "type": "object"
    },
    {
      "type": "null"
    }
  ],
  "title": "Body"
}
```

**Response 200:**
```json
{
  "properties": {
    "called_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Called At"
    },
    "cancelled_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancelled At"
    },
    "completed_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Completed At"
    },
    "counter_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Counter Id"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "processing_started_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Processing Started At"
    },
    "queue_entry_id": {
      "format": "uuid",
      "title": "Queue Entry Id",
      "type": "string"
    },
    "queue_id": {
      "format": "uuid",
      "title": "Queue Id",
      "type": "string"
    },
    "sequence_number": {
      "title": "Sequence Number",
      "type": "integer"
    },
    "status": {
      "enum": [
        "CHECK_IN",
        "TOKEN",
        "WAITING",
        "CALLED",
        "PROCESSING",
        "COMPLETED",
        "CANCELLED"
      ],
      "title": "TokenStatus",
      "type": "string"
    },
    "token_number": {
      "title": "Token Number",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "created_at",
    "token_number",
    "sequence_number",
    "queue_id",
    "queue_entry_id",
    "farmer_id",
    "status",
    "updated_at"
  ],
  "title": "TokenResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### POST /api/v1/queues/{id}/join

**Purpose:** Join Queue

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
```json
{
  "anyOf": [
    {
      "properties": {
        "farmer_id": {
          "anyOf": [
            {
              "format": "uuid",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "description": "Farmer ID (required for officers)",
          "title": "Farmer Id"
        }
      },
      "title": "QueueJoinRequest",
      "type": "object"
    },
    {
      "type": "null"
    }
  ],
  "title": "Body"
}
```

**Response 201:**
```json
{
  "properties": {
    "called_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Called At"
    },
    "cancelled_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancelled At"
    },
    "completed_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Completed At"
    },
    "counter_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Counter Id"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "processing_started_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Processing Started At"
    },
    "queue_entry_id": {
      "format": "uuid",
      "title": "Queue Entry Id",
      "type": "string"
    },
    "queue_id": {
      "format": "uuid",
      "title": "Queue Id",
      "type": "string"
    },
    "sequence_number": {
      "title": "Sequence Number",
      "type": "integer"
    },
    "status": {
      "enum": [
        "CHECK_IN",
        "TOKEN",
        "WAITING",
        "CALLED",
        "PROCESSING",
        "COMPLETED",
        "CANCELLED"
      ],
      "title": "TokenStatus",
      "type": "string"
    },
    "token_number": {
      "title": "Token Number",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "created_at",
    "token_number",
    "sequence_number",
    "queue_id",
    "queue_entry_id",
    "farmer_id",
    "status",
    "updated_at"
  ],
  "title": "TokenResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

## tokens

### GET /api/v1/tokens/{id}

**Purpose:** Get Token

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "called_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Called At"
    },
    "cancelled_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancelled At"
    },
    "completed_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Completed At"
    },
    "counter_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Counter Id"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "processing_started_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Processing Started At"
    },
    "queue_entry_id": {
      "format": "uuid",
      "title": "Queue Entry Id",
      "type": "string"
    },
    "queue_id": {
      "format": "uuid",
      "title": "Queue Id",
      "type": "string"
    },
    "sequence_number": {
      "title": "Sequence Number",
      "type": "integer"
    },
    "status": {
      "enum": [
        "CHECK_IN",
        "TOKEN",
        "WAITING",
        "CALLED",
        "PROCESSING",
        "COMPLETED",
        "CANCELLED"
      ],
      "title": "TokenStatus",
      "type": "string"
    },
    "token_number": {
      "title": "Token Number",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "created_at",
    "token_number",
    "sequence_number",
    "queue_id",
    "queue_entry_id",
    "farmer_id",
    "status",
    "updated_at"
  ],
  "title": "TokenResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### POST /api/v1/tokens/{id}/cancel

**Purpose:** Cancel Token

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "called_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Called At"
    },
    "cancelled_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancelled At"
    },
    "completed_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Completed At"
    },
    "counter_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Counter Id"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "processing_started_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Processing Started At"
    },
    "queue_entry_id": {
      "format": "uuid",
      "title": "Queue Entry Id",
      "type": "string"
    },
    "queue_id": {
      "format": "uuid",
      "title": "Queue Id",
      "type": "string"
    },
    "sequence_number": {
      "title": "Sequence Number",
      "type": "integer"
    },
    "status": {
      "enum": [
        "CHECK_IN",
        "TOKEN",
        "WAITING",
        "CALLED",
        "PROCESSING",
        "COMPLETED",
        "CANCELLED"
      ],
      "title": "TokenStatus",
      "type": "string"
    },
    "token_number": {
      "title": "Token Number",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "created_at",
    "token_number",
    "sequence_number",
    "queue_id",
    "queue_entry_id",
    "farmer_id",
    "status",
    "updated_at"
  ],
  "title": "TokenResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### POST /api/v1/tokens/{id}/complete

**Purpose:** Complete Token

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "called_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Called At"
    },
    "cancelled_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancelled At"
    },
    "completed_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Completed At"
    },
    "counter_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Counter Id"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "processing_started_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Processing Started At"
    },
    "queue_entry_id": {
      "format": "uuid",
      "title": "Queue Entry Id",
      "type": "string"
    },
    "queue_id": {
      "format": "uuid",
      "title": "Queue Id",
      "type": "string"
    },
    "sequence_number": {
      "title": "Sequence Number",
      "type": "integer"
    },
    "status": {
      "enum": [
        "CHECK_IN",
        "TOKEN",
        "WAITING",
        "CALLED",
        "PROCESSING",
        "COMPLETED",
        "CANCELLED"
      ],
      "title": "TokenStatus",
      "type": "string"
    },
    "token_number": {
      "title": "Token Number",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "created_at",
    "token_number",
    "sequence_number",
    "queue_id",
    "queue_entry_id",
    "farmer_id",
    "status",
    "updated_at"
  ],
  "title": "TokenResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```

### POST /api/v1/tokens/{id}/process

**Purpose:** Process Token

**Authentication:** required

**Path parameters:**
- id (string, format: uuid) — Id

**Query parameters:**
`none`

**Request body:**
`none`

**Response 200:**
```json
{
  "properties": {
    "called_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Called At"
    },
    "cancelled_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Cancelled At"
    },
    "completed_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Completed At"
    },
    "counter_id": {
      "anyOf": [
        {
          "format": "uuid",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Counter Id"
    },
    "created_at": {
      "format": "date-time",
      "title": "Created At",
      "type": "string"
    },
    "farmer_id": {
      "format": "uuid",
      "title": "Farmer Id",
      "type": "string"
    },
    "id": {
      "format": "uuid",
      "title": "Id",
      "type": "string"
    },
    "processing_started_at": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Processing Started At"
    },
    "queue_entry_id": {
      "format": "uuid",
      "title": "Queue Entry Id",
      "type": "string"
    },
    "queue_id": {
      "format": "uuid",
      "title": "Queue Id",
      "type": "string"
    },
    "sequence_number": {
      "title": "Sequence Number",
      "type": "integer"
    },
    "status": {
      "enum": [
        "CHECK_IN",
        "TOKEN",
        "WAITING",
        "CALLED",
        "PROCESSING",
        "COMPLETED",
        "CANCELLED"
      ],
      "title": "TokenStatus",
      "type": "string"
    },
    "token_number": {
      "title": "Token Number",
      "type": "string"
    },
    "updated_at": {
      "format": "date-time",
      "title": "Updated At",
      "type": "string"
    }
  },
  "required": [
    "id",
    "created_at",
    "token_number",
    "sequence_number",
    "queue_id",
    "queue_entry_id",
    "farmer_id",
    "status",
    "updated_at"
  ],
  "title": "TokenResponse",
  "type": "object"
}
```

**Response 422:**
```json
{
  "properties": {
    "detail": {
      "items": {
        "properties": {
          "ctx": {
            "title": "Context",
            "type": "object"
          },
          "input": {
            "title": "Input"
          },
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "title": "Location",
            "type": "array"
          },
          "msg": {
            "title": "Message",
            "type": "string"
          },
          "type": {
            "title": "Error Type",
            "type": "string"
          }
        },
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError",
        "type": "object"
      },
      "title": "Detail",
      "type": "array"
    }
  },
  "title": "HTTPValidationError",
  "type": "object"
}
```
