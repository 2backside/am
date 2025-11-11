<#
.SYNOPSIS
  Adiciona "New folder" do diretório atual como exclusão no Windows Defender.

.NOTES
  - Executa elevação automática se necessário.
  - Cria a pasta se não existir.
  - Uso: abra PowerShell e execute o script no diretório desejado:
      .\Add-DefenderExclusion-NewFolder.ps1

  Segurança: adicionar exclusões diminui a proteção. Só faça se souber o que está a excluir.
#>

# --- elevação ---
function Ensure-RunAsAdmin {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "Não está a correr como administrador. A pedir elevação..." -ForegroundColor Yellow
        Start-Process -FilePath pwsh -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
        exit
    }
}

Ensure-RunAsAdmin

# --- caminho da pasta alvo ---
$base = (Get-Location).ProviderPath
$targetFolderName = "New folder"
$targetPath = Join-Path -Path $base -ChildPath $targetFolderName

# criar a pasta se não existir (opcional)
if (-not (Test-Path -LiteralPath $targetPath)) {
    try {
        New-Item -Path $targetPath -ItemType Directory -Force | Out-Null
        Write-Host "Pasta criada: $targetPath"
    } catch {
        Write-Error "Falha ao criar a pasta '$targetPath': $($_.Exception.Message)"
        exit 1
    }
} else {
    Write-Host "Pasta já existe: $targetPath"
}

# --- verifica existência do cmdlet do Defender ---
if (-not (Get-Command -Name Add-MpPreference -ErrorAction SilentlyContinue)) {
    Write-Error "O cmdlet Add-MpPreference não está disponível nesta máquina. Verifique se o Windows Defender (Windows Defender Antivirus / Microsoft Defender) e os módulos de proteção estão instalados."
    exit 2
}

# --- adiciona exclusão (evita duplicados) ---
try {
    $prefs = Get-MpPreference
    if ($prefs.ExclusionPath -contains $targetPath) {
        Write-Host "O caminho já consta nas exclusões do Defender: $targetPath" -ForegroundColor Green
    } else {
        Add-MpPreference -ExclusionPath $targetPath
        Write-Host "Exclusão adicionada com sucesso: $targetPath" -ForegroundColor Green
    }

    # mostra lista atualizada (opcional)
    Write-Host "`nExclusões atuais (ExclusionPath):"
    (Get-MpPreference).ExclusionPath | ForEach-Object { Write-Host " - $_" }
} catch {
    Write-Error "Erro ao adicionar exclusão: $($_.Exception.Message)"
    exit 3
}
