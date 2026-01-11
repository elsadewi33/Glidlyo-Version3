import os
import pickle
import json
import time
import random
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

class YoutubeUploader:
    def __init__(self, client_secrets_file, credentials_file):
        self.client_secrets_file = client_secrets_file
        self.credentials_file = credentials_file
        # Standard YouTube Scopes
        self.scopes = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube']
        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        credentials = None
        
        # 1. Attempt to load the token
        if os.path.exists(self.credentials_file):
            try:
                # METHOD A: Try loading as JSON (New Standard)
                credentials = Credentials.from_authorized_user_file(self.credentials_file, self.scopes)
            except ValueError:
                # METHOD B: Fallback to Pickle (Old Way) if JSON fails
                try:
                    with open(self.credentials_file, 'rb') as token:
                        credentials = pickle.load(token)
                except Exception as e:
                    print(f"⚠️ Token Load Error: {e}")
            except Exception as e:
                print(f"⚠️ Unexpected Token Error: {e}")

        # 2. Refresh Token if expired
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print("🔄 Refreshing Access Token...")
                try:
                    credentials.refresh(Request())
                    
                    # Save the refreshed token back as JSON (Modern format)
                    with open(self.credentials_file, 'w') as token:
                        token.write(credentials.to_json())
                except Exception as e:
                    print(f"❌ Token Refresh Failed: {e}")
                    raise Exception("Token expired and refresh failed. Please re-authenticate.")
            else:
                # If we can't refresh, we must crash so the user knows to re-auth
                raise Exception("❌ Token is invalid or expired. Please run authentication again.")

        return build('youtube', 'v3', credentials=credentials)

    def upload_video(self, file_path, title, description, tags, category_id="22", localizations=None, thumbnail_path=None):
        # --- LOGIC UPDATE: Map models.py "modes" to YouTube Category IDs ---
        # 'car_restoration' -> 2 (Autos & Vehicles)
        # 'asmr'           -> 24 (Entertainment)
        # 'shorts'         -> 22 (People & Blogs - Default)
        mode_mapping = {
            "car_restoration": "2", 
            "asmr": "24",
            "shorts": "22",
            "Car Restorations": "2" # Keep for backward compatibility
        }
        
        # If the input matches a known mode, swap it for the ID
        if category_id in mode_mapping:
            print(f"🔄 Mode Detected '{category_id}': Switching Category ID to {mode_mapping[category_id]}")
            category_id = mode_mapping[category_id]
            
        print(f"🚀 Uploading to YouTube: {title}")
        print(f"   📂 Category ID: {category_id}")
        
        snippet = {
            'title': title[:100], # Max 100 chars
            'description': description[:5000], # Max 5000 chars
            'tags': tags.split(',') if isinstance(tags, str) else tags,
            'categoryId': category_id,
            'defaultLanguage': 'en',        # REQUIRED when using localizations
            'defaultAudioLanguage': 'en'    # Good practice
        }

        body = {
            'snippet': snippet,
            'status': {
                'privacyStatus': 'public', # Default to public
                'selfDeclaredMadeForKids': False,
                'containsSyntheticMedia': True  # REQUIRED: Sets "Altered content" flag to YES
            }
        }

        # Add Translations if provided
        if localizations:
            body['localizations'] = localizations

        # Upload Video File
        media = MediaFileUpload(file_path, chunksize=1024*1024, resumable=True)
        request = self.youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   ☁️ Uploading: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        print(f"✅ Upload Complete. Video ID: {video_id}")

        # Upload Thumbnail (if provided and valid)
        if thumbnail_path and os.path.exists(thumbnail_path) and video_id:
            try:
                print(f"🖼️ Uploading Thumbnail...")
                self.youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                print("✅ Thumbnail Set.")
            except Exception as e:
                print(f"⚠️ Thumbnail Upload Failed: {e}")

        return video_id
    
    def create_broadcast(self, title, description, privacy_status="public", scheduled_start_time=None):
        """
        Create a YouTube livestream broadcast.
        
        Args:
            title: Broadcast title
            description: Broadcast description
            privacy_status: Privacy setting (public, private, unlisted)
            scheduled_start_time: ISO 8601 format timestamp (e.g., "2026-01-11T21:00:00Z")
        
        Returns:
            Dictionary with broadcast_id, stream_id, and stream_url
        """
        from datetime import datetime, timezone, timedelta
        
        # If no scheduled_start_time provided, default to 5 minutes from now
        if not scheduled_start_time:
            now_utc = datetime.now(timezone.utc)
            scheduled_dt = now_utc + timedelta(minutes=5)
            scheduled_start_time = scheduled_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"📡 Creating livestream broadcast: {title}")
        print(f"   🕒 Scheduled Start: {scheduled_start_time}")
        print(f"   🔒 Privacy: {privacy_status}")
        
        # Step 1: Create the broadcast
        broadcast_body = {
            'snippet': {
                'title': title[:100],
                'description': description[:5000],
                'scheduledStartTime': scheduled_start_time
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            },
            'contentDetails': {
                'enableAutoStart': True,
                'enableAutoStop': True
            }
        }
        
        broadcast_response = self.youtube.liveBroadcasts().insert(
            part='snippet,status,contentDetails',
            body=broadcast_body
        ).execute()
        
        broadcast_id = broadcast_response['id']
        print(f"✅ Broadcast created. ID: {broadcast_id}")
        
        # Step 2: Create the livestream
        stream_body = {
            'snippet': {
                'title': f"{title} - Stream"
            },
            'cdn': {
                'frameRate': '30fps',
                'ingestionType': 'rtmp',
                'resolution': '1080p'
            }
        }
        
        stream_response = self.youtube.liveStreams().insert(
            part='snippet,cdn',
            body=stream_body
        ).execute()
        
        stream_id = stream_response['id']
        stream_url = stream_response['cdn']['ingestionInfo']['ingestionAddress']
        stream_key = stream_response['cdn']['ingestionInfo']['streamName']
        
        print(f"✅ Stream created. ID: {stream_id}")
        print(f"   📺 Stream URL: {stream_url}")
        
        # Step 3: Bind the stream to the broadcast
        self.youtube.liveBroadcasts().bind(
            part='id,contentDetails',
            id=broadcast_id,
            streamId=stream_id
        ).execute()
        
        print(f"✅ Broadcast bound to stream")
        
        return {
            'broadcast_id': broadcast_id,
            'stream_id': stream_id,
            'stream_url': stream_url,
            'stream_key': stream_key,
            'scheduled_start_time': scheduled_start_time
        }