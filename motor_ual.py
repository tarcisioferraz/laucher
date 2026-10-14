@echo off
chcp 65001 >nul
title UAL Client - Auto Updater
color 0B

:: Garante que o BAT rode exatamente na pasta onde ele esta salvo
cd /d "%~dp0"

:: =========================================================================
:: CONFIGURACAO: Coloque abaixo o link RAW do seu motor_ual.py no GitHub!
:: Para pegar o link Raw: Abra o arquivo no GitHub e clique no botao "Raw"
:: =========================================================================
set "GITHUB_RAW_URL=https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPOSITORIO/main/motor_ual.py"
set "ARQUIVO_LOCAL=motor_ual.py"
set "ARQUIVO_TEMP=motor_ual_temp.py"

echo ===================================================
echo            🌙 UAL CLIENT - AUTO UPDATER
echo ===================================================
echo.
echo [*] Verificando atualizacoes no GitHub...

:: Faz o download silencioso da versao do GitHub para um arquivo temporario
curl -s -L "%GITHUB_RAW_URL%" -o "%ARQUIVO_TEMP%"

:: Se falhar o download (sem internet ou link errado), abre o jogo local direto
if %errorlevel% neq 0 (
    echo [!] Sem conexao com o GitHub. Iniciando versao local...
    if exist "%ARQUIVO_TEMP%" del "%ARQUIVO_TEMP%"
    goto INICIAR
)

:: Verifica se o arquivo baixado nao veio vazio ou com erro 404
for %%A in ("%ARQUIVO_TEMP%") do if %%~zA==0 (
    echo [!] Arquivo remoto vazio ou URL invalida. Iniciando versao local...
    del "%ARQUIVO_TEMP%"
    goto INICIAR
)

:: Se o motor_ual.py ainda nao existir na pasta, instala direto
if not exist "%ARQUIVO_LOCAL%" (
    echo [+] Instalando o Motor UAL pela primeira vez...
    move /y "%ARQUIVO_TEMP%" "%ARQUIVO_LOCAL%" >nul
    goto INICIAR
)

:: Compara o arquivo local com o do GitHub byte a byte (comando fc)
fc /b "%ARQUIVO_LOCAL%" "%ARQUIVO_TEMP%" >nul
if %errorlevel% equ 0 (
    echo [OK] O seu UAL Client ja esta na versao mais recente!
    del "%ARQUIVO_TEMP%"
) else (
    echo [!] Nova atualizacao encontrada no GitHub!
    echo [*] Atualizando o %ARQUIVO_LOCAL%...
    move /y "%ARQUIVO_TEMP%" "%ARQUIVO_LOCAL%" >nul
    echo [OK] Atualizacao concluida com sucesso!
)

:INICIAR
echo.
echo [*] Iniciando UAL Client Launcher...
:: Usa start /b pythonw ou python para abrir o Launcher
start "" python "%ARQUIVO_LOCAL%"
exit
