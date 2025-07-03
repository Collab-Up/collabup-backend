<<<<<<< HEAD
# CollabUp Recommendation System Backend

This is the backend API for the CollabUp recommendation system that provides intelligent search and recommendation functionality across all platform collections.

## Features

- **Multi-Collection Search**: Searches across 4 collections simultaneously:
  - Student Projects (`studentProjects`)
  - Startup Projects (`startups`)
  - Mentor Profiles (`mentors`)
  - Research Projects (`researchProjects`)

- **Intelligent Scoring**: Uses semantic similarity and keyword matching to rank results
- **Real-time Recommendations**: Provides instant search results as users type
- **Firebase Integration**: Directly connects to your Firestore database

## Setup Instructions

### Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Firebase

1. Copy your `serviceAccountKey.json` from the main CollabUp directory to the backend directory:
   ```bash
   cp ../serviceAccountKey.json ./serviceAccountKey.json
   ```

2. Make sure your Firebase project has the following collections:
   - `studentProjects`
   - `startups`
   - `mentors`
   - `researchProjects`

### Step 3: Set Environment Variables

Create a `.env` file in the backend directory:
```bash
# Backend configuration
PORT=8000
HOST=0.0.0.0

# Firebase configuration (if needed)
FIREBASE_PROJECT_ID=your-project-id
```

### Step 4: Run the Backend

```bash
# Development mode with auto-reload
python recommendation_backend.py

# Or using uvicorn directly
uvicorn recommendation_backend:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### Step 5: Test the API

1. **Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Get Collections Info**:
   ```bash
   curl http://localhost:8000/collections-info
   ```

3. **Test Recommendations**:
   ```bash
   curl -X POST http://localhost:8000/recommend \
     -H "Content-Type: application/json" \
     -d '{"query": "machine learning", "top_n": 3}'
   ```

## API Endpoints

### POST `/recommend`
Get recommendations from all collections based on search query.

**Request Body**:
```json
{
  "query": "machine learning python",
  "top_n": 5
}
```

**Response**:
```json
{
  "student_projects": [...],
  "startup_projects": [...],
  "mentor_profiles": [...],
  "research_projects": [...]
}
```

### GET `/health`
Health check endpoint.

### GET `/collections-info`
Get information about available collections and document counts.

## Frontend Integration

### Step 1: Set Environment Variable

Add to your frontend `.env` file:
```bash
VITE_RECOMMENDATION_API_URL=http://localhost:8000
```

### Step 2: The recommendation service is already integrated in:
- `src/services/recommendationService.ts` - API service
- `src/components/Navbar.tsx` - Search functionality

## How It Works

### 1. Search Query Processing
- Parses user input into tokens
- Handles multiple formats (comma-separated, space-separated)
- Converts to lowercase for matching

### 2. Similarity Scoring
Each collection has specific scoring rules:

**Student Projects**:
- Title matches: +3.0 points
- Domain matches: +2.5 points
- Technology matches: +2.0 points
- Description matches: +1.5 points

**Startup Projects**:
- Title matches: +3.0 points
- Domain matches: +2.5 points
- Skills matches: +2.0 points
- Company matches: +2.0 points
- Description matches: +1.5 points

**Mentor Profiles**:
- Expertise matches: +3.0 points
- Company matches: +2.0 points
- Name matches: +2.0 points
- Bio matches: +1.5 points

**Research Projects**:
- Title matches: +3.0 points
- Domain matches: +2.5 points
- Skills matches: +2.0 points
- Description matches: +1.5 points

### 3. Result Ranking
- Sorts by similarity score (highest first)
- Returns top N results per collection
- Includes similarity scores in response

## Database Schema Requirements

### Student Projects Collection
```json
{
  "title": "string",
  "description": "string",
  "domain": "string",
  "level": "string",
  "technologies": ["string"],
  "duration": "string",
  "location": "string",
  "projectOwnerEmail": "string",
  "ownerId": "string",
  "ownerEmail": "string",
  "ownerName": "string"
}
```

### Startup Projects Collection
```json
{
  "title": "string",
  "description": "string",
  "domain": "string",
  "skills": ["string"],
  "company": "string",
  "location": "string"
}
```

### Mentors Collection
```json
{
  "name": "string",
  "expertise": ["string"],
  "bio": "string",
  "currentCompany": "string",
  "designation": "string"
}
```

### Research Projects Collection
```json
{
  "title": "string",
  "description": "string",
  "domain": "string",
  "skills": ["string"],
  "level": "string"
}
```

## Performance Considerations

1. **Debounced Search**: Frontend waits 500ms after user stops typing
2. **Limited Results**: Returns only top 3-5 results per collection
3. **Efficient Queries**: Uses Firebase streaming for real-time data
4. **Caching**: Consider implementing Redis for frequently searched terms

## Troubleshooting

### Common Issues

1. **Firebase Connection Error**:
   - Verify `serviceAccountKey.json` is in the backend directory
   - Check Firebase project permissions

2. **Import Errors**:
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.8+ required)

3. **No Results**:
   - Verify collections exist in Firebase
   - Check collection names match exactly
   - Ensure documents have required fields

4. **CORS Issues**:
   - Add CORS middleware if needed for production

### Debug Mode

Enable debug logging by setting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

1. **Environment Variables**:
   - Set `VITE_RECOMMENDATION_API_URL` to production URL
   - Use production Firebase credentials

2. **Security**:
   - Enable CORS properly
   - Add rate limiting
   - Use HTTPS

3. **Scaling**:
   - Consider using async processing for large datasets
   - Implement caching layer
   - Use load balancer for multiple instances

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify Firebase configuration
3. Test with the provided curl commands
4. Check browser console for frontend errors 
=======
# collabup-backend
This contains the backend part of CollabUp
>>>>>>> 72301940509aef842886a53a9b85cf557515a855
