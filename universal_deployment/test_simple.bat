@echo off
echo 🧪 Testing BUDDY Universal Core
echo ==============================
echo.

echo 📊 Container Status:
docker-compose -f docker-compose-simple.yml ps
echo.

echo 🏥 Testing Health Endpoint:
curl -s http://localhost:8000/ || echo "Service not ready yet"
echo.

echo 💬 Testing Chat Endpoint:
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"text\":\"Hello BUDDY!\"}" || echo "Chat endpoint not ready yet"
echo.

echo 🗄️ Testing Database Connection:
docker-compose -f docker-compose-simple.yml exec -T postgres psql -U buddy -d buddydb -c "SELECT COUNT(*) FROM chat_logs;" || echo "Database not ready yet"
echo.

echo ✅ Test completed!
pause
