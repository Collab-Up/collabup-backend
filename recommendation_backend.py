import json
import os
from typing import List, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import re
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

app = FastAPI(title="CollabUp Recommendation System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase Admin SDK
try:
    print("🔧 Initializing Firebase Admin SDK...")
    cred = credentials.Certificate("serviceAccountKey.json")
    print("✅ Service account key loaded successfully")
    
    # Check if Firebase app is already initialized
    try:
        firebase_admin.get_app()
        print("⚠️ Firebase app already initialized, using existing app")
    except ValueError:
        firebase_admin.initialize_app(cred)
        print("✅ Firebase app initialized successfully")
    
    db = firestore.client()
    print("✅ Firestore client created successfully")
    
    # Test the connection
    try:
        test_collection = db.collection('projects').limit(1).stream()
        test_count = len(list(test_collection))
        print(f"✅ Firebase connection test successful. Found {test_count} documents in projects collection")
    except Exception as e:
        print(f"❌ Firebase connection test failed: {e}")
        db = None
        
except FileNotFoundError:
    print("❌ serviceAccountKey.json not found in backend directory")
    db = None
except Exception as e:
    print(f"❌ Error initializing Firebase: {e}")
    import traceback
    traceback.print_exc()
    db = None

class SearchInput(BaseModel):
    query: str
    top_n: int = 5

class RecommendationResponse(BaseModel):
    student_projects: List[Dict[str, Any]]
    startup_projects: List[Dict[str, Any]]
    mentor_profiles: List[Dict[str, Any]]
    research_projects: List[Dict[str, Any]]

# Define query categories and their associated keywords
QUERY_CATEGORIES = {
    'skills': ['skill', 'technology', 'tech', 'programming', 'language', 'framework', 'tool', 'expertise', 'proficient', 'know', 'learn', 'master'],
    'domains': ['domain', 'field', 'area', 'industry', 'sector', 'vertical', 'category', 'type', 'kind'],
    'locations': ['location', 'place', 'city', 'remote', 'onsite', 'hybrid', 'bangalore', 'mumbai', 'delhi', 'hyderabad', 'chennai', 'pune'],
    'companies': ['company', 'startup', 'organization', 'firm', 'enterprise', 'corporate', 'google', 'microsoft', 'amazon', 'meta', 'apple'],
    'institutes': ['college', 'university', 'institute', 'iit', 'nit', 'bits', 'school', 'academy'],
    'roles': ['role', 'position', 'job', 'title', 'designation', 'professor', 'mentor', 'student', 'developer', 'engineer'],
    'experience': ['experience', 'years', 'senior', 'junior', 'fresher', 'expert', 'beginner', 'intermediate', 'advanced'],
    'projects': ['project', 'work', 'build', 'develop', 'create', 'implement', 'design', 'research', 'study']
}

def parse_search_query(query: str) -> Dict[str, List[str]]:
    """Parse search query into categorized tokens"""
    query_lower = query.lower().strip()
    
    # Split on various delimiters
    tokens = re.split(r'[;,\n\t]+|\s{2,}|\s+', query_lower)
    tokens = [t.strip() for t in tokens if t.strip() and len(t) > 1]
    
    categorized_tokens = {
        'skills': [],
        'domains': [],
        'locations': [],
        'companies': [],
        'institutes': [],
        'roles': [],
        'experience': [],
        'projects': [],
        'general': []
    }
    
    for token in tokens:
        categorized = False
        
        # Check each category
        for category, keywords in QUERY_CATEGORIES.items():
            if any(keyword in token or token in keyword for keyword in keywords):
                categorized_tokens[category].append(token)
                categorized = True
                break
        
        # If not categorized, add to general
        if not categorized:
            categorized_tokens['general'].append(token)
    
    return categorized_tokens

def calculate_fuzzy_similarity(text1: str, text2: str) -> float:
    """Calculate fuzzy similarity between two strings"""
    if not text1 or not text2:
        return 0.0
    
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    
    # Exact match gets highest score
    if text1_lower == text2_lower:
        return 1.0
    
    # Contains match
    if text1_lower in text2_lower or text2_lower in text1_lower:
        return 0.8
    
    # Word-level matching
    words1 = set(text1_lower.split())
    words2 = set(text2_lower.split())
    
    if words1 and words2:
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        if union:
            jaccard_similarity = len(intersection) / len(union)
            return jaccard_similarity * 0.6
    
    # Sequence matcher for partial matches
    return SequenceMatcher(None, text1_lower, text2_lower).ratio() * 0.4

def calculate_similarity_score(categorized_tokens: Dict[str, List[str]], item_data: Dict[str, Any], item_type: str) -> float:
    """Calculate comprehensive similarity score between query and item data"""
    score = 0.0
    
    # Extract all text fields from the item
    all_text_fields = []
    
    if item_type == "student_projects":
        # Student projects fields
        title = item_data.get('title', '')
        description = item_data.get('description', '')
        skills_required = item_data.get('skillsRequired', [])
        domain = item_data.get('domain', '')
        difficulty = item_data.get('difficulty', '')
        type_project = item_data.get('type', '')
        
        all_text_fields = [
            ('title', title, 3.0),
            ('description', description, 1.5),
            ('domain', domain, 2.5),
            ('difficulty', difficulty, 1.0),
            ('type', type_project, 1.0)
        ]
        
        # Handle skills array
        for skill in skills_required:
            all_text_fields.append(('skill', skill, 2.0))
            
    elif item_type == "startup_projects":
        # Startup fields
        name = item_data.get('name', '')
        description = item_data.get('description', '')
        domain = item_data.get('domain', '')
        location = item_data.get('location', '')
        mission = item_data.get('mission', '')
        founder = item_data.get('founder', '')
        funding = item_data.get('funding', '')
        
        all_text_fields = [
            ('name', name, 3.0),
            ('description', description, 1.5),
            ('domain', domain, 2.5),
            ('location', location, 1.5),
            ('mission', mission, 2.0),
            ('founder', founder, 1.0),
            ('funding', funding, 0.5)
        ]
        
    elif item_type == "mentor_profiles":
        # Mentor fields
        name = item_data.get('name', '')
        expertise = item_data.get('expertise', [])
        bio = item_data.get('bio', '')
        current_company = item_data.get('currentCompany', '')
        designation = item_data.get('designation', '')
        experience = str(item_data.get('experience', ''))
        
        all_text_fields = [
            ('name', name, 2.0),
            ('bio', bio, 1.5),
            ('currentCompany', current_company, 2.0),
            ('designation', designation, 1.5),
            ('experience', experience, 1.0)
        ]
        
        # Handle expertise array
        for exp in expertise:
            all_text_fields.append(('expertise', exp, 3.0))
            
    elif item_type == "research_projects":
        # Faculty/Research fields
        name = item_data.get('name', '')
        research_areas = item_data.get('researchAreas', [])
        bio = item_data.get('bio', '')
        department = item_data.get('department', '')
        institute = item_data.get('institute', '')
        designation = item_data.get('designation', '')
        experience = str(item_data.get('experience', ''))
        
        all_text_fields = [
            ('name', name, 2.0),
            ('bio', bio, 1.5),
            ('department', department, 2.0),
            ('institute', institute, 1.5),
            ('designation', designation, 1.5),
            ('experience', experience, 1.0)
        ]
        
        # Handle research areas array
        for area in research_areas:
            all_text_fields.append(('researchArea', area, 3.0))
    
    # Calculate scores for each category of tokens
    for category, tokens in categorized_tokens.items():
        if not tokens:
            continue
            
        for token in tokens:
            max_token_score = 0.0
            
            # Check against all text fields
            for field_name, field_value, field_weight in all_text_fields:
                if not field_value:
                    continue
                
                # Convert field value to string if it's not already
                field_str = str(field_value)
                
                # Calculate similarity
                similarity = calculate_fuzzy_similarity(token, field_str)
                token_score = similarity * field_weight
                
                max_token_score = max(max_token_score, token_score)
            
            # Add category-specific bonuses
            if category == 'skills' and item_type in ['student_projects', 'mentor_profiles']:
                max_token_score *= 1.2
            elif category == 'domains' and item_type in ['student_projects', 'startup_projects']:
                max_token_score *= 1.2
            elif category == 'companies' and item_type == 'mentor_profiles':
                max_token_score *= 1.2
            elif category == 'institutes' and item_type == 'research_projects':
                max_token_score *= 1.2
            elif category == 'locations' and item_type == 'startup_projects':
                max_token_score *= 1.2
            
            score += max_token_score
    
    # Add bonus for having multiple matching tokens
    total_tokens = sum(len(tokens) for tokens in categorized_tokens.values())
    if total_tokens > 1 and score > 0:
        score *= 1.1  # 10% bonus for multiple matches
    
    return score

async def get_recommendations_from_firebase(query: str, top_n: int = 5) -> RecommendationResponse:
    """Get recommendations from Firebase collections"""
    if not db:
        raise HTTPException(status_code=500, detail="Firebase not initialized")
    
    print(f"🔍 Processing query: '{query}'")
    
    # Parse query into categories
    categorized_tokens = parse_search_query(query)
    print(f"📝 Query categories: {categorized_tokens}")
    
    # Check if we have any meaningful tokens
    total_tokens = sum(len(tokens) for tokens in categorized_tokens.values())
    if total_tokens == 0:
        print("⚠️ No meaningful tokens found in query")
        return RecommendationResponse(
            student_projects=[],
            startup_projects=[],
            mentor_profiles=[],
            research_projects=[]
        )
    
    try:
        # Fetch data from correct collections
        projects_ref = db.collection('projects')
        startups_ref = db.collection('startups')
        mentors_ref = db.collection('mentors')
        faculty_ref = db.collection('faculty')
        
        print("📊 Fetching data from collections...")
        
        # Get documents from each collection
        projects_docs = projects_ref.stream()
        startups_docs = startups_ref.stream()
        mentors_docs = mentors_ref.stream()
        faculty_docs = faculty_ref.stream()
        
        # Convert to dictionaries and calculate scores
        student_projects = []
        startup_projects = []
        mentor_profiles = []
        research_projects = []
        
        # Process projects (student projects)
        print("🔍 Processing student projects...")
        for doc in projects_docs:
            data = doc.to_dict()
            data['id'] = doc.id
            score = calculate_similarity_score(categorized_tokens, data, "student_projects")
            if score > 0.1:  # Lower threshold for better recall
                data['similarity_score'] = score
                student_projects.append(data)
        print(f"   Found {len(student_projects)} matching student projects")
        
        # Process startups (startup projects)
        print("🔍 Processing startup projects...")
        for doc in startups_docs:
            data = doc.to_dict()
            data['id'] = doc.id
            score = calculate_similarity_score(categorized_tokens, data, "startup_projects")
            if score > 0.1:
                data['similarity_score'] = score
                startup_projects.append(data)
        print(f"   Found {len(startup_projects)} matching startup projects")
        
        # Process mentors (mentor profiles)
        print("🔍 Processing mentor profiles...")
        for doc in mentors_docs:
            data = doc.to_dict()
            data['id'] = doc.id
            score = calculate_similarity_score(categorized_tokens, data, "mentor_profiles")
            if score > 0.1:
                data['similarity_score'] = score
                mentor_profiles.append(data)
        print(f"   Found {len(mentor_profiles)} matching mentor profiles")
        
        # Process faculty (research projects)
        print("🔍 Processing research projects...")
        for doc in faculty_docs:
            data = doc.to_dict()
            data['id'] = doc.id
            score = calculate_similarity_score(categorized_tokens, data, "research_projects")
            if score > 0.1:
                data['similarity_score'] = score
                research_projects.append(data)
        print(f"   Found {len(research_projects)} matching research projects")
        
        # Sort by similarity score and get top N
        student_projects.sort(key=lambda x: x['similarity_score'], reverse=True)
        startup_projects.sort(key=lambda x: x['similarity_score'], reverse=True)
        mentor_profiles.sort(key=lambda x: x['similarity_score'], reverse=True)
        research_projects.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        result = RecommendationResponse(
            student_projects=student_projects[:top_n],
            startup_projects=startup_projects[:top_n],
            mentor_profiles=mentor_profiles[:top_n],
            research_projects=research_projects[:top_n]
        )
        
        print(f"✅ Final results: {len(result.student_projects)} + {len(result.startup_projects)} + {len(result.mentor_profiles)} + {len(result.research_projects)} = {len(result.student_projects) + len(result.startup_projects) + len(result.mentor_profiles) + len(result.research_projects)} total")
        
        return result
    except Exception as e:
        print(f"❌ Error fetching recommendations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching recommendations: {str(e)}")

@app.post('/recommend', response_model=RecommendationResponse)
async def recommend_profiles(input: SearchInput):
    """
    Get recommendations from all collections based on search query
    """
    try:
        print(f"🔍 Recommendation request: {input.query}")
        recommendations = await get_recommendations_from_firebase(input.query, input.top_n)
        
        # Log the results
        total_results = (len(recommendations.student_projects) + 
                        len(recommendations.startup_projects) + 
                        len(recommendations.mentor_profiles) + 
                        len(recommendations.research_projects))
        
        print(f"✅ Found {total_results} total recommendations")
        print(f"   Student Projects: {len(recommendations.student_projects)}")
        print(f"   Startup Projects: {len(recommendations.startup_projects)}")
        print(f"   Mentor Profiles: {len(recommendations.mentor_profiles)}")
        print(f"   Research Projects: {len(recommendations.research_projects)}")
        
        return recommendations
    except Exception as e:
        print(f"❌ Error in recommendation endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")

@app.get('/health')
async def health_check():
    """Health check endpoint"""
    try:
        status = "healthy"
        firebase_status = "connected"
        collections_info = {}
        
        if not db:
            status = "unhealthy"
            firebase_status = "not connected"
        else:
            # Test Firebase connection by checking collections
            try:
                collections = ['projects', 'startups', 'mentors', 'faculty']
                for collection_name in collections:
                    try:
                        docs = list(db.collection(collection_name).limit(1).stream())
                        collections_info[collection_name] = {
                            "status": "accessible",
                            "sample_count": len(docs)
                        }
                    except Exception as e:
                        collections_info[collection_name] = {
                            "status": "error",
                            "error": str(e)
                        }
                        firebase_status = "partial"
            except Exception as e:
                firebase_status = "error"
                status = "unhealthy"
        
        return {
            "status": status,
            "firebase_status": firebase_status,
            "collections": collections_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get('/debug-query')
async def debug_query(query: str = Query(..., description="Search query to debug")):
    """Debug endpoint to understand query processing"""
    if not db:
        raise HTTPException(status_code=500, detail="Firebase not initialized")
    
    try:
        print(f"🔍 Debugging query: {query}")
        
        # Parse query into categories
        categorized_tokens = parse_search_query(query)
        print(f"📝 Categorized tokens: {categorized_tokens}")
        
        # Get sample data from each collection
        sample_data = {}
        
        # Get one sample from each collection
        collections = ['projects', 'startups', 'mentors', 'faculty']
        for collection_name in collections:
            try:
                docs = list(db.collection(collection_name).limit(1).stream())
                if docs:
                    sample_data[collection_name] = docs[0].to_dict()
                    print(f"✅ Got sample from {collection_name}")
                else:
                    print(f"⚠️ No data in {collection_name}")
            except Exception as e:
                print(f"❌ Error getting sample from {collection_name}: {e}")
        
        # Calculate sample scores
        sample_scores = {}
        for collection_name, data in sample_data.items():
            try:
                if collection_name == 'projects':
                    score = calculate_similarity_score(categorized_tokens, data, "student_projects")
                    sample_scores['student_projects'] = score
                elif collection_name == 'startups':
                    score = calculate_similarity_score(categorized_tokens, data, "startup_projects")
                    sample_scores['startup_projects'] = score
                elif collection_name == 'mentors':
                    score = calculate_similarity_score(categorized_tokens, data, "mentor_profiles")
                    sample_scores['mentor_profiles'] = score
                elif collection_name == 'faculty':
                    score = calculate_similarity_score(categorized_tokens, data, "research_projects")
                    sample_scores['research_projects'] = score
                print(f"📊 Score for {collection_name}: {sample_scores.get(list(sample_scores.keys())[-1] if sample_scores else 'unknown')}")
            except Exception as e:
                print(f"❌ Error calculating score for {collection_name}: {e}")
                sample_scores[collection_name] = 0.0
        
        result = {
            "query": query,
            "categorized_tokens": categorized_tokens,
            "sample_scores": sample_scores,
            "sample_data": sample_data
        }
        
        print(f"✅ Debug result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Error in debug endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error debugging query: {str(e)}")

@app.get('/collections-info')
async def get_collections_info():
    """Get information about available collections"""
    if not db:
        raise HTTPException(status_code=500, detail="Firebase not initialized")
    
    try:
        collections = ['projects', 'startups', 'mentors', 'faculty']
        info = {}
        
        for collection_name in collections:
            docs = db.collection(collection_name).stream()
            count = len(list(docs))
            info[collection_name] = {
                "count": count,
                "description": get_collection_description(collection_name)
            }
        
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting collections info: {str(e)}")

def get_collection_description(collection_name: str) -> str:
    """Get description for each collection"""
    descriptions = {
        "projects": "Student-created projects looking for collaborators",
        "startups": "Startup projects and opportunities",
        "mentors": "Professional mentors available for guidance",
        "faculty": "Academic faculty and research projects"
    }
    return descriptions.get(collection_name, "Unknown collection")

# For local development
if __name__ == "__main__":
    uvicorn.run("recommendation_backend:app", host="0.0.0.0", port=8000, reload=True) 