<div align="center">
  <img src="https://raw.githubusercontent.com/odoo/odoo/17.0/addons/web/static/img/odoo_logo.svg" alt="Odoo Logo" width="160"/>

  # Salon ERP Module for Odoo 19
  
  **A complete suite for managing salon bookings, staff scheduling, service catalogs, and customer loyalty rewards.**

</div>

---

## Overview

**Salon ERP** provides a streamlined, end-to-end workflow for salon and spa operations within Odoo 19. It simplifies appointment management, eliminates scheduling conflicts, tracks technician availability, and automates customer loyalty rewards.

---

## Core Features

- 📅 **Appointment Management**: Seamless scheduling with automated time slot conflict checks.
- ✂️ **Staff & Resource Allocation**: Assign stylists, set working calendars, and track service specializations.
- 🏷️ **Service Catalog**: Configurable duration, pricing, and categorizations for all salon offerings.
- 🎁 **Customer Loyalty Program**: Automatically earn and redeem loyalty points on completed bookings.
- 📊 **Dashboards & Analytics**: Real-time insights into appointments, staff utilization, and sales.

---

## Module Workflow

```
Customer Booking  ➜  Staff Allocation  ➜  Service Delivery & Checkout  ➜  Loyalty Points Credit
```

---

## Installation & Configuration

### Prerequisites
- **Odoo 19.0** (Community or Enterprise)
- Dependencies: `base`, `mail`, `resource`

### Quick Setup

1. **Clone Repository**:
   ```bash
   git clone https://github.com/Chirudeva-Reddy/odoo-salon-erp.git salon_erp
   ```

2. **Add to Addons Path** (`odoo.conf`):
   ```ini
   addons_path = /path/to/custom_addons,/path/to/odoo/addons
   ```

3. **Install Module**:
   - Enable **Developer Mode** in Odoo.
   - Go to **Apps** ➜ **Update Apps List**.
   - Search for **Salon ERP** and click **Install**.

---

## Data Models & Security

### Core Models

| Model | Description |
| :--- | :--- |
| `salon.booking` | Primary record for salon customer appointments |
| `salon.booking.line` | Line items for services selected per booking |
| `salon.service` | Catalog of offered services, pricing, and default durations |
| `salon.staff` | Technician profiles, skills, and working schedules |
| `salon.loyalty.ledger` | Audit log for earned and redeemed customer loyalty points |
| `res.partner` (extended) | Adds customer loyalty points balance tracking |

### Access Rights
- **Salon User**: Create bookings, view services, and check customer points.
- **Salon Manager**: Full control over pricing, staff configuration, and loyalty rules.

---

## Testing

Run unit tests via Odoo CLI:

```bash
./odoo-bin -c odoo.conf -i salon_erp --test-enable --stop-after-init
```

---

## License

Distributed under the **LGPL-3.0 License**.
