
# 🍽️ Waiter

A contactless restaurant ordering system. Customers scan a QR code on their table, browse the menu, place an order, and track it live — all from their phone. Staff see new orders instantly on their dashboard without refreshing the page.

🔗 Live Demo: [waiterrr.onrender.com](https://waiterrr.onrender.com/)

---

## How it works

1. Restaurant owner creates a restaurant, adds tables and a menu
2. Each table gets an auto-generated QR code
3. Customer scans the QR → browses menu → adds to cart → places order
4. Staff dashboard receives the order instantly via WebSocket
5. Staff updates the order status (Accepted → Making → Completed)
6. Customer sees the status update live on their screen

---

## Tech Stack

|                  | Technology                       |
| ---------------- | -------------------------------- |
| Backend          | Django 5.1                       |
| Real-time        | Django Channels 4 + WebSocket    |
| ASGI Server      | Daphne                           |
| REST API         | Django REST Framework            |
| Database         | SQLite (dev) / PostgreSQL (prod) |
| Channel Layer    | In-Memory (dev) / Redis (prod)   |
| Frontend         | Django Templates + Vite          |
| Static Files     | Whitenoise                       |
| Media Storage    | Local / AWS S3 / Cloudinary      |
| Background Tasks | Celery                           |
| QR Codes         | qrcode                           |

---

## Project Structure

```
waiter-master/
├── waiter/
│   ├── asgi.py         # Routes HTTP vs WebSocket traffic
│   ├── settings.py     # All configuration
│   └── urls.py         # Root URL config
├── common/
│   ├── models.py       # All database models
│   ├── views.py        # Page views + REST API views
│   ├── consumers.py    # WebSocket handler (real-time orders)
│   ├── routing.py      # WebSocket URL routing + middleware
│   ├── serializers.py  # Model → JSON converters
│   ├── taxonomies.py   # Enums (OrderStatus, MenuType, PriceType)
│   ├── urls.py         # All HTTP URL patterns
│   └── templates/      # HTML templates
```

---

## Getting Started

1. Clone and install dependencies

```bash
git clone <repo-url>
cd waiter-master
pip install -r requirements.txt
```

2. Set up environment variables

```bash
cp .env.template .env
# Fill in the values in .env
```

3. Run migrations and start the server

```bash
python manage.py migrate
daphne waiter.asgi:application
```

Visit `http://localhost:8000` — log in at `/login/` to access the dashboard.

---

## Environment Variables

| Variable              | Description                              |
| --------------------- | ---------------------------------------- |
| `DJANGO_SECRET_KEY` | Django secret key                        |
| `DEBUG`             | `True` for dev, `False` for prod     |
| `ALLOWED_HOSTS`     | Comma-separated allowed hostnames        |
| `BASE_URL`          | Used to generate QR code URLs            |
| `AWS_STORAGE_*`     | S3 credentials (only if `USE_S3=True`) |

---

## Key Pages

| URL                              | Who uses it | What it does        |
| -------------------------------- | ----------- | ------------------- |
| `/`                            | Everyone    | Home page           |
| `/login/`                      | Staff       | Login               |
| `/dashboard/`                  | Staff       | List of restaurants |
| `/dashboard/restaurant/<uid>/` | Staff       | Tables + categories |
| `/dashboard/order/<uid>/`      | Staff       | Live order feed     |
| `/table/<uid>/`                | Customer    | Browse menu         |
| `/table/<uid>/order/`          | Customer    | View & place order  |

---

## Real-Time Orders (WebSocket)

The app uses Django Channels to push order updates to the browser without any page refresh.

Connection URL: `ws/order/<uid>/`

- Staff connects with a restaurant UID → watches all orders for that restaurant
- Customer connects with their session UID → watches their own orders

What happens when a customer places an order:

```
Customer submits order
    → Order saved to DB
    → WebSocket push to customer's session group  (customer sees their order)
    → WebSocket push to restaurant group          (staff dashboard updates)
```

What happens when staff updates an order status:

```
Staff clicks "Accept" on dashboard
    → WebSocket message sent to server
    → Order status updated in DB
    → WebSocket push to customer's session group  (customer sees "Accepted")
    → WebSocket push to restaurant group          (dashboard reflects change)
```

---

## Future Improvements

### Must-have

- Switch channel layer to Redis — the current in-memory layer doesn't work across multiple server processes, so it will break in any real production deployment
- Switch database to PostgreSQL — SQLite is not suitable for production; it doesn't handle concurrent writes well
- Online payment integration — currently there's no way to pay; adding Razorpay or Stripe would complete the ordering flow
- Proper customer authentication — right now customers are tracked only by session cookie, which breaks if they clear cookies or switch browsers

### Should-have

- Order history for customers — customers have no way to see past orders after their session ends
- Push notifications — notify staff on mobile when a new order arrives, even if the dashboard tab is in the background
- Menu item images — the model supports images but the upload flow in the dashboard needs improvement
- Table-level bill splitting — allow multiple customers at the same table to split the bill
- Estimated wait time — show customers an approximate time before their order is ready

### Nice-to-have

- Multi-language support — the project has `USE_I18N = True` but translations aren't set up yet
- Analytics dashboard — most ordered items, peak hours, revenue per day
- Printer integration — auto-print order tickets in the kitchen when an order is placed
- Dark mode for the customer-facing menu
- Accessibility improvements — better screen reader support and keyboard navigation

---

## Documentation

For a deeper dive into the architecture, models, WebSocket flow, and API endpoints, see [DOCUMENTATION.md](./DOCUMENTATION.md).
