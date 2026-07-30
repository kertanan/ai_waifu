import asyncio
import pyvts

plugin_info = {
    "plugin_name": "AI Waifu",
    "developer": "Ferdy",
    "authentication_token_path": "./token.txt"
}

async def main():
    vts = pyvts.vts(plugin_info=plugin_info)
    
    print("Menyambungkan ke VTube Studio...")
    await vts.connect()
    
    print("Minta akses... Cepat buka jendela VTube Studio dan klik ALLOW!")
    await vts.request_authenticate_token()
    
    await vts.request_authenticate()
    print("Berhasil! Coba cek folder kamu, pasti ada file 'token.txt' sekarang.")
    
    await vts.close()

if __name__ == "__main__":
    asyncio.run(main())