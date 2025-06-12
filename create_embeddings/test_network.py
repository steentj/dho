import aiohttp
import asyncio
import ssl
import socket
from aiohttp import TCPConnector

async def test_network_connectivity():
    """Test network connectivity from Docker container"""
    
    print("=== Network Connectivity Test ===")
    
    # Test 1: DNS Resolution
    print("\n1. Testing DNS resolution...")
    try:
        ip = socket.gethostbyname('slaegtsbibliotek.dk')
        print(f"✓ DNS resolution successful: slaegtsbibliotek.dk -> {ip}")
    except Exception as e:
        print(f"✗ DNS resolution failed: {e}")
    
    # Test 2: Basic HTTP connectivity
    print("\n2. Testing HTTP connectivity...")
    ssl_context = ssl.create_default_context()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(
        connector=TCPConnector(ssl=ssl_context),
        headers=headers,
        timeout=timeout
    ) as session:
        
        # Test URLs
        test_urls = [
            ('Google', 'https://www.google.com/'),
            ('HTTPBin (shows our IP)', 'https://httpbin.org/ip'),
            ('Main site', 'https://slaegtsbibliotek.dk/'),
            ('Target PDF', 'https://slaegtsbibliotek.dk/2024/904382.pdf')
        ]
        
        for name, url in test_urls:
            try:
                print(f"\nTesting {name}: {url}")
                async with session.get(url, timeout=30) as response:
                    print(f"  Status: {response.status}")
                    print(f"  Server: {response.headers.get('Server', 'Unknown')}")
                    
                    if 'httpbin' in url and response.status == 200:
                        content = await response.text()
                        print(f"  Our IP: {content.strip()}")
                    
                    if response.status == 503:
                        print("  ⚠️  503 Service Unavailable - likely blocking")
                        print(f"  Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                        
            except asyncio.TimeoutError:
                print(f"  ✗ Timeout connecting to {name}")
            except Exception as e:
                print(f"  ✗ Error connecting to {name}: {e}")
            
            await asyncio.sleep(1)  # Be nice to servers

if __name__ == "__main__":
    asyncio.run(test_network_connectivity())