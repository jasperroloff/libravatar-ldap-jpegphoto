import os
from waitress import serve
from app import create_app

listen_port = int(os.environ.get('PORT', default=5000))

serve(create_app(), listen=f"*:{listen_port}")
