# TCG List Scraper

A web application to scrape and display TCG card lists from mytcgcollection.com with sortable and searchable results.

## Features

- 🔍 Scrape TCG card lists by URL
- 📊 View card details: Name, Set, Rarity, Image
- 🔄 Sort by any column (Name, Set, Rarity)
- 🔎 Search/filter cards in real-time
- 🎨 Beautiful, responsive UI

## Project Structure

```
tcg-list-extra-info/
├── backend/           # Python Flask API
│   ├── app.py        # Main API server with scraping logic
│   └── requirements.txt
└── frontend/         # React application
    ├── public/
    ├── src/
    └── package.json
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Flask server:
```bash
python app.py
```

The backend will start on `http://localhost:5000`

> **Note:** A virtual environment is optional but recommended for isolation. The app works fine with global Python packages.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will start on `http://localhost:3000` and open in your browser.

## Usage

1. Make sure both backend and frontend servers are running
2. Open `http://localhost:3000` in your browser
3. Enter a TCG list URL (e.g., `https://mytcgcollection.com/p/noahark8/list/d695e74a-ba64-46e6-8c5d-e796e2768a9b`)
4. Click "Scrape List" and wait for the results
5. Use the search box to filter cards
6. Click on column headers to sort

## API Endpoints

### POST /api/scrape
Scrape a TCG list and return card data.

**Request:**
```json
{
  "url": "https://mytcgcollection.com/p/.../list/..."
}
```

**Response:**
```json
{
  "success": true,
  "cards": [
    {
      "name": "Card Name",
      "set": "Set Name",
      "rarity": "Rare",
      "image_url": "https://...",
      "card_url": "https://..."
    }
  ],
  "total": 42
}
```

### GET /api/health
Health check endpoint.

## Technologies Used

### Backend
- Flask - Web framework
- BeautifulSoup4 - Web scraping
- Requests - HTTP library
- Flask-CORS - Cross-origin support

### Frontend
- React - UI framework
- Axios - HTTP client
- CSS3 - Styling

## Notes

- The scraper includes a 0.5 second delay between requests to be respectful to the server
- Large lists may take several minutes to scrape completely
- The application only works with mytcgcollection.com URLs

## License

MIT
