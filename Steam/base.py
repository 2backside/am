#!/usr/bin/env python3
"""
Steam Lua Downloader
Downloader simplificado para arquivos .lua de jogos Steam.

Baseado no projeto Steam Depot Online original.
"""

import asyncio
import aiohttp
import aiofiles
import os
import json
import vdf
from typing import List, Tuple, Optional
import sys

# Configuração de repositórios (baseado no repositories.json original)
REPOSITORIES = {
    # Repositórios Encrypted
    "Fairyvmos/BlankTMing": "Encrypted",
    "sean-who/ManifestAutoUpdate": "Encrypted",
    "Fallonma/ManifestAutoUpdate_btm": "Encrypted",
    "nekoaday/ManifestAutoUpdate": "Encrypted",
    "nekoaday/ManifestAutoUpdate_again": "Encrypted",
    "Scropiouos/ManifestAutoUpdate_PrivateBackUp": "Encrypted",
    
    # Repositórios Decrypted
    "ManifestHub/ManifestHub": "Decrypted",
    "ikun0014/ManifestHub": "Decrypted",
    "Auiowu/ManifestAutoUpdate": "Decrypted",
    "tymolu233/ManifestAutoUpdate": "Decrypted",
    "tymolu233/ManifestAutoUpdate-fix": "Decrypted",
    "luomojim/ManifestAutoUpdate": "Decrypted",
    "hansaes/ManifestAutoUpdate": "Decrypted",
    "MineRPG/ManifestAutoUpdate": "Decrypted",
    "bingyu50/SteamManifestCache": "Decrypted",
    "bingyu50/ManifestAutoUpdate": "Decrypted",
    "TOP-01/ManifestAutoUpdate": "Decrypted",
    "TOP-01/SteamManifestCache": "Decrypted",
    "Scropiouos/ManifestAutoUpdate_backup": "Decrypted",
    "Scropiouos/SteamManifestCache_backup": "Decrypted",
    "ltsj/ManifestAutoUpdate": "Decrypted",
    "1271620983/ManifestAutoUpdate": "Decrypted",
    "crazzzzzysnail/ManifestAutoUpdate_fork": "Decrypted",
    
    # Repositórios Branch
    "SteamAutoCracks/ManifestHub": "Branch",
    "Fairyvmos/bruh-hub": "Branch",
    "japapalarox/ManifestHubPrivado": "Branch"
}

class SimpleLuaDownloader:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_file_from_github(self, repo: str, sha: str, path: str) -> Optional[bytes]:
        """Baixa um arquivo do GitHub usando múltiplos CDNs como fallback"""
        url_list = [
            f"https://gcore.jsdelivr.net/gh/{repo}@{sha}/{path}",
            f"https://fastly.jsdelivr.net/gh/{repo}@{sha}/{path}",
            f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{path}",
            f"https://ghproxy.org/https://raw.githubusercontent.com/{repo}/{sha}/{path}",
            f"https://raw.dgithub.xyz/{repo}/{sha}/{path}",
            f"https://raw.githubusercontent.com/{repo}/{sha}/{path}",
        ]
        
        for url in url_list:
            try:
                async with self.session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.read()
            except Exception as e:
                print(f"Erro ao baixar de {url}: {e}")
                continue
        return None
    
    async def get_branch_info(self, repo: str, appid: str) -> Optional[dict]:
        """Obtém informações sobre o branch do AppID no repositório"""
        try:
            url = f"https://api.github.com/repos/{repo}/branches/{appid}"
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"Erro ao obter informações do branch {appid} em {repo}: {e}")
        return None
    
    async def get_file_tree(self, repo: str, sha: str) -> Optional[dict]:
        """Obtém a árvore de arquivos do commit"""
        try:
            url = f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1"
            async with self.session.get(url, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"Erro ao obter árvore de arquivos de {repo}: {e}")
        return None
    
    def parse_vdf_to_lua(self, depot_info: List[Tuple[str, str]], appid: str) -> str:
        """Converte informações VDF em script Lua"""
        lua_lines = [f"addappid({appid})"]
        
        for depot_id, decryption_key in depot_info:
            lua_lines.append(f'addappid({depot_id},1,"{decryption_key}")')
        
        return "\n".join(lua_lines)
    
    def parse_vdf_file(self, vdf_content: bytes) -> List[Tuple[str, str]]:
        """Extrai chaves de descriptografia de um arquivo VDF"""
        depot_info = []
        try:
            vdf_data = vdf.loads(vdf_content.decode('utf-8'))
            
            # Procura por chaves de descriptografia no VDF
            if 'depots' in vdf_data:
                for depot_id, depot_data in vdf_data['depots'].items():
                    if isinstance(depot_data, dict) and 'DecryptionKey' in depot_data:
                        key = depot_data['DecryptionKey']
                        if key and key != '0' * len(key):  # Verifica se não é uma chave vazia
                            depot_info.append((depot_id, key))
        except Exception as e:
            print(f"Erro ao processar arquivo VDF: {e}")
        
        return depot_info
    
    async def download_appid_data(self, appid: str) -> bool:
        """Baixa dados do AppID e gera arquivo Lua"""
        print(f"Procurando dados para AppID: {appid}")
        
        depot_info = []
        found_data = False
        
        # Procura em repositórios Decrypted primeiro (mais provável de ter chaves válidas)
        # Depois tenta Encrypted, e por último Branch
        repo_priority = ["Decrypted", "Encrypted", "Branch"]
        
        for priority in repo_priority:
            for repo, repo_type in REPOSITORIES.items():
                if repo_type != priority:
                    continue
                
            print(f"Verificando repositório: {repo}")
            
            # Obtém informações do branch
            branch_info = await self.get_branch_info(repo, appid)
            if not branch_info:
                continue
                
            sha = branch_info['commit']['sha']
            print(f"Branch encontrado em {repo}, SHA: {sha}")
            
            # Obtém árvore de arquivos
            tree_info = await self.get_file_tree(repo, sha)
            if not tree_info:
                continue
            
            # Procura por arquivos key.vdf ou config.vdf
            vdf_files = []
            for file_info in tree_info.get('tree', []):
                if file_info['type'] == 'blob':
                    filename = file_info['path'].split('/')[-1]
                    if filename.lower() in ['key.vdf', 'config.vdf']:
                        vdf_files.append(file_info)
            
            if not vdf_files:
                print(f"Nenhum arquivo VDF encontrado em {repo}")
                continue
            
            # Baixa e processa arquivos VDF
            for vdf_file in vdf_files:
                print(f"Baixando {vdf_file['path']} de {repo}")
                vdf_content = await self.get_file_from_github(repo, sha, vdf_file['path'])
                
                if vdf_content:
                    file_depot_info = self.parse_vdf_file(vdf_content)
                    depot_info.extend(file_depot_info)
                    found_data = True
                    print(f"Encontradas {len(file_depot_info)} chaves de descriptografia")
            
            if found_data:
                break
            
            # Se for repositório Branch, tenta baixar o zip diretamente
            if repo_type == "Branch":
                print(f"Tentando baixar zip direto de {repo}")
                zip_url = f"https://api.github.com/repos/{repo}/zipball/{appid}"
                try:
                    async with self.session.get(zip_url, timeout=60) as response:
                        if response.status == 200:
                            zip_content = await response.read()
                            zip_filename = f"{appid}_branch.zip"
                            async with aiofiles.open(zip_filename, 'wb') as f:
                                await f.write(zip_content)
                            print(f"✅ Zip baixado com sucesso: {zip_filename}")
                            found_data = True
                            break
                except Exception as e:
                    print(f"Erro ao baixar zip de {repo}: {e}")
                    continue
        
        if not found_data:
            print(f"Nenhum dado encontrado para AppID {appid}")
            return False
        
        # Gera arquivo Lua
        lua_content = self.parse_vdf_to_lua(depot_info, appid)
        lua_filename = f"{appid}.lua"
        
        # Salva arquivo Lua na raiz do projeto
        try:
            async with aiofiles.open(lua_filename, 'w', encoding='utf-8') as f:
                await f.write(lua_content)
            print(f"Arquivo Lua salvo como: {lua_filename}")
            print(f"Conteúdo do arquivo:")
            print("-" * 40)
            print(lua_content)
            print("-" * 40)
            return True
        except Exception as e:
            print(f"Erro ao salvar arquivo Lua: {e}")
            return False

async def main():
    """Função principal"""
    import sys
    
    # Verifica se foi chamado com argumento (modo não-interativo)
    if len(sys.argv) > 1:
        appid = sys.argv[1].strip()
        if not appid.isdigit():
            print("❌ AppID deve conter apenas números")
            sys.exit(1)
        
        # Baixa dados do AppID
        async with SimpleLuaDownloader() as downloader:
            success = await downloader.download_appid_data(appid)
            
            if success:
                print(f"\n✅ Sucesso! Arquivo {appid}.lua foi criado.")
                sys.exit(0)
            else:
                print(f"\n❌ Falha ao baixar dados para AppID {appid}")
                print("Verifique se o jogo existe nos repositórios.")
                sys.exit(1)
    
    # Modo interativo (comportamento original)
    print("=" * 60)
    print("Steam Lua Downloader")
    print("=" * 60)
    print("Downloader simplificado para arquivos .lua de jogos Steam")
    print("Baseado no projeto Steam Depot Online original")
    print("=" * 60)
    
    # Pede o AppID
    while True:
        try:
            appid = input("\nDigite o AppID do jogo (ou 'sair' para encerrar): ").strip()
            
            if appid.lower() in ['sair', 'exit', 'quit']:
                print("Encerrando...")
                break
            
            if not appid.isdigit():
                print("Por favor, digite um AppID válido (apenas números)")
                continue
            
            # Baixa dados do AppID
            async with SimpleLuaDownloader() as downloader:
                success = await downloader.download_appid_data(appid)
                
                if success:
                    print(f"\n✅ Sucesso! Arquivo {appid}.lua foi criado na raiz do projeto.")
                else:
                    print(f"\n❌ Falha ao baixar dados para AppID {appid}")
                    print("Tente outro AppID ou verifique se o jogo existe nos repositórios.")
        
        except KeyboardInterrupt:
            print("\n\nEncerrando...")
            break
        except Exception as e:
            print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    # Configuração para Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma encerrado pelo usuário.")
