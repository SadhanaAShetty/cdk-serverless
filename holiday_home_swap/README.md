# Holiday Home Swap API

A FastAPI-based platform for home exchange between travelers. Users can list their homes, create swap requests, and get matched with other homeowners for mutual exchanges.

## Features

###  Current Features
- **User Management**: Registration, authentication with JWT tokens
- **Home Listings**: Create detailed home listings with photos, amenities, and house rules
- **Swap Bids**: Request home swaps for specific locations and dates
- **Smart Matching**: Automatic matching algorithm based on location and date overlap
- **Email Notifications**: AWS SES integration for match notifications
- **Image Storage**: AWS S3 integration with image optimization
- **User Preferences**: Customizable swap preferences and notification settings


## Tech Stack

- **Backend**: FastAPI, Python 3.9+
- **Database**: SQLite (SQLAlchemy ORM)
- **Authentication**: JWT tokens
- **Cloud**: AWS (S3, SES, SNS)
- **Infrastructure**: AWS CDK
- **Containerization**: Docker

## Quick Start


### Installation



## How It Works

1. **Register & Setup Profile**: Create account and set swap preferences
2. **List Your Home**: Add your home with photos, amenities, and availability
3. **Create Swap Bids**: Request swaps for desired locations and dates
4. **Get Matched**: System automatically finds compatible swaps
5. **Get Notified**: Receive email notifications for new matches
6. **Connect**: Exchange contact details after both parties accept

## AWS Setup
- S3 bucket for home images
- SNS topic for notifications
- SES for email alert
- SSM parameters for configuration








