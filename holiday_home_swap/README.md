# Holiday Home Swap API

A FastAPI-based platform for home exchange between travelers. Users can list their homes, create swap requests, and get matched with other homeowners for mutual exchanges.

## What it does
- Users sign up and list their homes
- Create swap requests for places they want to visit
- System finds matches between users
- Users accept or reject matches
- Email notifications for new matches

### Core Functionality
- User Management: Registration, JWT authentication, and profile management
- Home Listings: Detailed home listings with photos, amenities, house rules, and availability
- Matching: Automatic matching algorithm based on location, dates, and user preferences
- Swap Bidding: Create and manage swap requests for specific locations and dates
- Match Management: Accept/reject matches with status tracking


## Tech used

- **Backend**: FastAPI with Python
- **Database**: SQLite
- **Cloud**: AWS S3 (photos), AWS SES (emails)
- **Infrastructure**: AWS CDK for IaaC
- **Testing**: 56+ test cases


API runs at `http://localhost:8000`


### Key Endpoints

#### Authentication
- `POST /api/v1/users` - Register new user
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user info

#### Home Management
- `POST /api/v1/homes` - Create home listing
- `GET /api/v1/homes/{id}` - Get specific home
- `GET /api/v1/listings` - List all homes
- `POST /api/v1/homes/{id}/photos` - Upload home photos

#### Swap System
- `POST /api/v1/swap_bids` - Create swap bid
- `GET /api/v1/swap_bids` - List user's bids
- `GET /api/v1/matches` - Get user's matches
- `PUT /api/v1/matches/{id}/accept` - Accept match
- `PUT /api/v1/matches/{id}/reject` - Reject match



## API docs

Visit `http://localhost:8000/docs` for full API documentation.


## Security Features

- JWT Authentication: Secure token-based authentication
- Password Hashing: Secure password storage
- Input Validation: Pydantic schema validation
- File Upload Security: Image type and size validation
- AWS IAM: Proper AWS service permissions











