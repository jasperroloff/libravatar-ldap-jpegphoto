import os
from waitress import serve
from app import create_app

serve(create_app(), port=int(os.environ.get('PORT', default=5000)))
