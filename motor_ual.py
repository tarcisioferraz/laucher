import pygame
import zipfile
import os
import sys
import re
import math
import random
import json
import traceback
import tempfile
import io
import queue
import threading
import urllib.error
import urllib.request
import tkinter as tk
from tkinter import messagebox, ttk

# FIX DE QUALIDADE DE IMAGEM (ALTA DEFINIÇÃO NO WINDOWS)
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ==========================================
# MOTOR GRÁFICO E INTERPRETADOR UAL 9.0
# ==========================================
class MotorUalGrafico:
    def __init__(self, config, caminho_arquivo_ual=None, codigo_puro=None):
        self.config = config
        pygame.init()
        try: pygame.mixer.init() 
        except: pass
        pygame.font.init()  
        
        self.largura = 800
        self.altura = 600
        
        self.tela_cheia = False
        self.tela = pygame.display.set_mode((self.largura, self.altura))
        pygame.display.set_caption("UAL Client 9.1 - Ultimate Engine")
        if config.get("fullscreen", False):
            self.definir_tela_cheia(True)
        
        self.clock = pygame.time.Clock()
        self.fonte_hud = pygame.font.SysFont("segoeui", 16, bold=True)
        
        self.fator_fps = 1.0 
        self.rodando = True
        self.cor_fundo = (15, 17, 26)
        
        # Variáveis de Efeitos Especiais (Screen Shake)
        self.shake_tempo = 0
        self.shake_intensidade = 0.0
        
        self.sprites = {}
        self.textos = {}
        self.sons = {}
        self.fundo = None
        self.eventos_tecla = {}
        self.eventos_segurar = {}
        self.eventos_segurar_mover = {}
        self.eventos_clique = {}
        self.cenas = {}
        self.variaveis = {}
        self.temporizadores = {}
        self.deslizamentos = {}
        self.alvos = {}
        self.profundidade_nova_cena = 0
        self.pasta_temp = ""
        self._diretorio_temp = None
        
        if caminho_arquivo_ual:
            if not caminho_arquivo_ual.lower().endswith(".ual"):
                raise Exception("Formato inválido! O motor aceita exclusivamente pacotes '.ual'.")
                
            diretorio_temp = tempfile.TemporaryDirectory(prefix="ual_jogo_")
            self.pasta_temp = diretorio_temp.name
            try:
                with zipfile.ZipFile(caminho_arquivo_ual, 'r') as zip_ref:
                    arquivos = zip_ref.infolist()
                    if sum(info.file_size for info in arquivos) > 250_000_000:
                        raise ValueError(
                            "O conteúdo descompactado do pacote excede 250 MB."
                        )
                    for info in arquivos:
                        nome_seguro = info.filename.replace("\\", "/")
                        partes = nome_seguro.split("/")
                        destino = os.path.abspath(
                            os.path.join(self.pasta_temp, *partes)
                        )
                        if (
                            nome_seguro.startswith("/")
                            or any(parte == ".." for parte in partes)
                            or (partes and ":" in partes[0])
                            or os.path.commonpath((self.pasta_temp, destino))
                            != os.path.abspath(self.pasta_temp)
                        ):
                            raise ValueError(
                                f"Caminho inválido dentro do pacote UAL: {info.filename}"
                            )
                    scripts = [
                        info.filename for info in arquivos
                        if os.path.basename(info.filename.replace("\\", "/")).casefold()
                        == "main.ualscript"
                    ]
                    if not scripts:
                        raise Exception(
                            "Arquivo 'main.ualscript' não encontrado dentro do pacote .ual!"
                        )
                    if len(scripts) > 1:
                        raise ValueError(
                            "O pacote UAL contém mais de um arquivo main.ualscript."
                        )
                    for info in arquivos:
                        zip_ref.extract(info, self.pasta_temp)

                caminho_codigo = os.path.join(self.pasta_temp, *scripts[0].replace("\\", "/").split("/"))
                if not os.path.exists(caminho_codigo):
                    raise Exception(
                        "Arquivo 'main.ualscript' não encontrado dentro do pacote .ual!"
                    )
                self.pasta_temp = os.path.dirname(caminho_codigo)

                with open(caminho_codigo, "r", encoding="utf-8") as f:
                    self.codigo = f.read().strip().split('\n')
            except Exception:
                diretorio_temp.cleanup()
                self.pasta_temp = ""
                pygame.quit()
                raise
            self._diretorio_temp = diretorio_temp
                
        elif codigo_puro:
            self.codigo = codigo_puro.strip().split('\n')
        else:
            raise Exception("Nenhum código encontrado.")
            
        for i, linha in enumerate(self.codigo):
            linha = linha.strip()
            if linha.startswith("CENA "):
                partes = linha.split()
                if len(partes) > 1:
                    self.cenas[partes[1].strip()] = i
            elif linha.startswith("variavel "):
                partes = linha.replace("variavel ", "").split("=")
                if len(partes) == 2:
                    nome = partes[0].strip()
                    valor = partes[1].strip()
                    if self.pasta_temp and valor.startswith("pp/"): 
                        valor = valor.replace("pp", self.pasta_temp, 1)
                    elif self.pasta_temp and valor == "pp": 
                        valor = self.pasta_temp
                    self.variaveis[nome] = valor

    def formatar_caminho(self, caminho):
        if self.pasta_temp and not caminho.startswith(self.pasta_temp):
            caminho = os.path.join(self.pasta_temp, caminho)
        return os.path.normpath(caminho)

    def definir_tela_cheia(self, ativar):
        self.tela_cheia = bool(ativar)
        self.config["fullscreen"] = self.tela_cheia
        if self.tela_cheia:
            self.tela = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.tela = pygame.display.set_mode((self.largura, self.altura))

    def alternar_tela_cheia(self):
        self.definir_tela_cheia(not self.tela_cheia)

    def converter_posicao_mouse(self, posicao):
        if not self.tela_cheia:
            return posicao
        tela_largura, tela_altura = self.tela.get_size()
        escala = min(tela_largura / self.largura, tela_altura / self.altura)
        area_largura = self.largura * escala
        area_altura = self.altura * escala
        margem_x = (tela_largura - area_largura) / 2
        margem_y = (tela_altura - area_altura) / 2
        return (
            (posicao[0] - margem_x) / escala,
            (posicao[1] - margem_y) / escala,
        )

    def resolver_texto(self, texto_bruto):
        for var, val in self.variaveis.items():
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            texto_bruto = texto_bruto.replace(f"{{{var}}}", str(val))
        return texto_bruto

    def sincronizar_pos(self, sp, novo_x, novo_y):
        sp["x"] = float(novo_x)
        sp["y"] = float(novo_y)
        sp["rect"].x = int(round(sp["x"]))
        sp["rect"].y = int(round(sp["y"]))

    def converter_numero(self, valor):
        valor = self.variaveis.get(valor, valor)
        return float(valor)

    def executar_repeticoes(self, quantidade, nome_cena, usar_delta):
        quantidade = float(quantidade)
        if not quantidade.is_integer():
            raise ValueError("REPETIR_CENA exige uma quantidade inteira.")
        quantidade = int(quantidade)
        if quantidade < 0 or quantidade > 1000:
            raise ValueError("REPETIR_CENA aceita uma quantidade entre 0 e 1000.")
        for _ in range(quantidade):
            if not self.rodando:
                break
            self.chamar_cena(nome_cena, usar_delta)

    def chamar_cena(self, nome_cena, usar_delta=False):
        if self.profundidade_nova_cena >= 32:
            raise RuntimeError("Limite de 32 chamadas aninhadas de cena excedido.")
        self.profundidade_nova_cena += 1
        try:
            self.executar_bloco(nome_cena, usar_delta)
        finally:
            self.profundidade_nova_cena -= 1

    def rebater_raquete(self, bola, raquete):
        if bola not in self.sprites or raquete not in self.sprites:
            return False

        sp_bola = self.sprites[bola]
        sp_raquete = self.sprites[raquete]
        if not sp_bola["visivel"] or not sp_raquete["visivel"]:
            return False

        rect_bola = sp_bola["rect"]
        rect_raquete = sp_raquete["rect"]
        inicio_y = sp_bola.get("prev_y", sp_bola["y"])
        if sp_bola["vy"] <= 0 or inicio_y >= rect_raquete.top:
            return False

        cruzou_topo = (
            rect_bola.bottom >= rect_raquete.top
            and inicio_y + rect_bola.height <= rect_raquete.top
        )
        if not rect_bola.colliderect(rect_raquete) and not cruzou_topo:
            return False

        x_contato = sp_bola["x"]
        if cruzou_topo:
            delta_y = sp_bola["y"] - inicio_y
            if delta_y <= 0:
                return False
            tempo_impacto = (rect_raquete.top - rect_bola.height - inicio_y) / delta_y
            x_contato = sp_bola.get("prev_x", sp_bola["x"]) + (
                sp_bola["x"] - sp_bola.get("prev_x", sp_bola["x"])
            ) * tempo_impacto
            if x_contato + rect_bola.width <= rect_raquete.left or x_contato >= rect_raquete.right:
                return False

        deslocamento = (
            x_contato + rect_bola.width / 2 - rect_raquete.centerx
        ) / max(rect_raquete.width / 2, 1)
        deslocamento = max(-1.0, min(1.0, deslocamento))
        velocidade = max(math.hypot(sp_bola["vx"], sp_bola["vy"]), 5.0)
        angulo = deslocamento * math.radians(60)

        self.sincronizar_pos(
            sp_bola,
            x_contato,
            rect_raquete.top - rect_bola.height - 1,
        )
        sp_bola["prev_x"] = sp_bola["x"]
        sp_bola["prev_y"] = sp_bola["y"]
        sp_bola["vx"] = velocidade * math.sin(angulo)
        sp_bola["vy"] = -velocidade * math.cos(angulo)
        return True

    def rebater_trajetoria(self, nome, obstaculo):
        if nome not in self.sprites or obstaculo not in self.sprites:
            return False

        sp = self.sprites[nome]
        alvo = self.sprites[obstaculo]
        if not sp["visivel"] or not alvo["visivel"]:
            return False

        rect = sp["rect"]
        limite = alvo["rect"]
        inicio_x = sp.get("prev_x", sp["x"])
        inicio_y = sp.get("prev_y", sp["y"])
        delta_x = sp["x"] - inicio_x
        delta_y = sp["y"] - inicio_y
        if delta_x == 0 and delta_y == 0:
            return False

        esquerda = limite.left - rect.width
        direita = limite.right
        topo = limite.top - rect.height
        baixo = limite.bottom

        if delta_x > 0:
            entrada_x = (esquerda - inicio_x) / delta_x
            saida_x = (direita - inicio_x) / delta_x
        elif delta_x < 0:
            entrada_x = (direita - inicio_x) / delta_x
            saida_x = (esquerda - inicio_x) / delta_x
        else:
            entrada_x = -math.inf if esquerda <= inicio_x <= direita else math.inf
            saida_x = math.inf

        if delta_y > 0:
            entrada_y = (topo - inicio_y) / delta_y
            saida_y = (baixo - inicio_y) / delta_y
        elif delta_y < 0:
            entrada_y = (baixo - inicio_y) / delta_y
            saida_y = (topo - inicio_y) / delta_y
        else:
            entrada_y = -math.inf if topo <= inicio_y <= baixo else math.inf
            saida_y = math.inf

        tempo_entrada = max(entrada_x, entrada_y)
        tempo_saida = min(saida_x, saida_y)
        if tempo_entrada > tempo_saida or tempo_saida < 0 or tempo_entrada > 1:
            return False

        tempo_impacto = max(tempo_entrada, 0)
        x = inicio_x + delta_x * tempo_impacto
        y = inicio_y + delta_y * tempo_impacto
        if entrada_x > entrada_y:
            x = esquerda - 1 if delta_x > 0 else direita + 1
            sp["vx"] = -sp["vx"]
        elif entrada_y > entrada_x:
            y = topo - 1 if delta_y > 0 else baixo + 1
            sp["vy"] = -sp["vy"]
        else:
            x = esquerda - 1 if delta_x > 0 else direita + 1
            y = topo - 1 if delta_y > 0 else baixo + 1
            sp["vx"] = -sp["vx"]
            sp["vy"] = -sp["vy"]

        self.sincronizar_pos(sp, x, y)
        sp["prev_x"] = sp["x"]
        sp["prev_y"] = sp["y"]
        return True

    def atualizar_movimentos_especiais(self):
        for nome, destino in list(self.deslizamentos.items()):
            sp = self.sprites.get(nome)
            if not sp or not sp["visivel"]:
                continue

            dx = destino["x"] - sp["x"]
            dy = destino["y"] - sp["y"]
            distancia = math.hypot(dx, dy)
            passo = destino["velocidade"] * self.fator_fps
            if distancia <= passo or distancia == 0:
                self.sincronizar_pos(sp, destino["x"], destino["y"])
                del self.deslizamentos[nome]
            else:
                self.sincronizar_pos(
                    sp,
                    sp["x"] + dx / distancia * passo,
                    sp["y"] + dy / distancia * passo,
                )

        for nome, alvo in list(self.alvos.items()):
            sp = self.sprites.get(nome)
            alvo_sp = self.sprites.get(alvo["sprite"])
            if not sp or not sp["visivel"] or not alvo_sp or not alvo_sp["visivel"]:
                continue

            dx = alvo_sp["x"] - sp["x"]
            dy = alvo_sp["y"] - sp["y"]
            distancia = math.hypot(dx, dy)
            passo = alvo["velocidade"] * self.fator_fps
            if distancia > passo and distancia > 0:
                self.sincronizar_pos(
                    sp,
                    sp["x"] + dx / distancia * passo,
                    sp["y"] + dy / distancia * passo,
                )

    def executar_bloco(self, nome_cena, usar_delta=False):
        if nome_cena not in self.cenas or not self.rodando: return
        escala = self.fator_fps if usar_delta else 1.0
            
        linha_idx = self.cenas[nome_cena] + 1
        while linha_idx < len(self.codigo) and self.rodando:
            linha = self.codigo[linha_idx].strip()
            
            if linha == "FIM_CENA" or linha.startswith("CENA"): break
            if not linha or linha.startswith("variavel ") or linha.startswith("#"):
                linha_idx += 1
                continue
                
            for nome_var, valor_var in self.variaveis.items():
                if not linha.startswith(("VAR_", "CRIAR_TEXTO", "ATUALIZAR_TEXTO", "SE_VAR_")):
                    linha = linha.replace(nome_var, str(valor_var))
                
            partes = linha.split()
            if not partes:
                linha_idx += 1
                continue
                
            comando = partes[0]
            
            try:
                if comando == "DEFINIR_TELA":
                    self.largura, self.altura = int(partes[1]), int(partes[2])
                    self.definir_tela_cheia(self.tela_cheia)

                # ================= NOVO: TELA CHEIA VIA SCRIPT =================
                elif comando == "TELA_CHEIA":
                    modo = partes[1].upper()
                    self.definir_tela_cheia(modo in ("LIGAR", "SIM", "TRUE", "ON"))
                
                elif comando == "DEFINIR_FUNDO_COR":
                    self.cor_fundo = (int(partes[1]), int(partes[2]), int(partes[3]))

                elif comando == "VAR_CRIAR": self.variaveis[partes[1]] = float(partes[2]) if "." in partes[2] else int(partes[2])
                elif comando == "VAR_SOMA": self.variaveis[partes[1]] += float(partes[2]) if "." in partes[2] else int(partes[2])
                elif comando == "VAR_SUBTRAIR": self.variaveis[partes[1]] -= float(partes[2]) if "." in partes[2] else int(partes[2])
                elif comando == "VAR_MULTIPLICAR":
                    self.variaveis[partes[1]] *= self.converter_numero(partes[2])
                elif comando == "VAR_DIVIDIR":
                    divisor = self.converter_numero(partes[2])
                    if divisor == 0:
                        raise ValueError("VAR_DIVIDIR não aceita divisão por zero.")
                    self.variaveis[partes[1]] /= divisor
                elif comando == "VAR_RESTO":
                    divisor = self.converter_numero(partes[2])
                    if divisor == 0:
                        raise ValueError("VAR_RESTO não aceita divisor zero.")
                    self.variaveis[partes[1]] %= divisor
                elif comando == "VAR_ALEATORIA":
                    minimo = self.converter_numero(partes[2])
                    maximo = self.converter_numero(partes[3])
                    if minimo > maximo:
                        raise ValueError("VAR_ALEATORIA exige mínimo menor ou igual ao máximo.")
                    if minimo.is_integer() and maximo.is_integer():
                        self.variaveis[partes[1]] = random.randint(int(minimo), int(maximo))
                    else:
                        self.variaveis[partes[1]] = random.uniform(minimo, maximo)
                elif comando == "VAR_COPIAR":
                    if partes[2] not in self.variaveis:
                        raise ValueError(f"Variável não encontrada: {partes[2]}")
                    self.variaveis[partes[1]] = self.variaveis[partes[2]]
                elif comando == "VAR_ARREDONDAR":
                    casas = int(partes[2]) if len(partes) > 2 else 0
                    self.variaveis[partes[1]] = round(self.converter_numero(partes[1]), casas)
                    
                elif comando == "SE_VAR_IGUAL":
                    if float(self.variaveis.get(partes[1], 0)) == float(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_MENOR":
                    if float(self.variaveis.get(partes[1], 0)) < float(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_MAIOR":
                    if float(self.variaveis.get(partes[1], 0)) > float(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_DIFERENTE":
                    if self.converter_numero(partes[1]) != self.converter_numero(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_MENOR_IGUAL":
                    if self.converter_numero(partes[1]) <= self.converter_numero(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_MAIOR_IGUAL":
                    if self.converter_numero(partes[1]) >= self.converter_numero(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_ENTRE":
                    valor = self.converter_numero(partes[1])
                    minimo = self.converter_numero(partes[2])
                    maximo = self.converter_numero(partes[3])
                    if minimo <= valor <= maximo:
                        self.executar_bloco(partes[4], usar_delta)
                elif comando == "SE_SPRITE_VISIVEL":
                    nome_sprite = partes[1]
                    if nome_sprite in self.sprites and self.sprites[nome_sprite]["visivel"]:
                        self.executar_bloco(partes[2], usar_delta)
                elif comando == "CHAMAR_CENA":
                    self.chamar_cena(partes[1], usar_delta)
                elif comando == "REPETIR_CENA":
                    self.executar_repeticoes(
                        self.converter_numero(partes[1]),
                        partes[2],
                        usar_delta,
                    )
                elif comando == "AGENDAR_CENA":
                    identificador = partes[1]
                    if identificador not in self.temporizadores:
                        atraso = self.converter_numero(partes[2])
                        if atraso < 0:
                            raise ValueError("AGENDAR_CENA exige um atraso igual ou maior que zero.")
                        self.temporizadores[identificador] = (
                            pygame.time.get_ticks() + int(atraso * 1000),
                            partes[3],
                        )
                elif comando == "CANCELAR_CENA_AGENDADA":
                    self.temporizadores.pop(partes[1], None)
                
                elif comando == "TOCAR_MUSICA":
                    try: pygame.mixer.music.load(self.formatar_caminho(partes[1])); pygame.mixer.music.play(-1)
                    except: pass
                elif comando == "PARAR_MUSICA": pygame.mixer.music.stop()
                elif comando == "TOCAR_SOM":
                    caminho_som = self.formatar_caminho(partes[1])
                    try:
                        if caminho_som not in self.sons: self.sons[caminho_som] = pygame.mixer.Sound(caminho_som)
                        self.sons[caminho_som].play()
                    except: pass

                # NOVO: Tocar som com volume específico (0 a 100)
                elif comando == "TOCAR_SOM_VOLUME":
                    caminho_som = self.formatar_caminho(partes[1])
                    vol = float(partes[2]) / 100.0
                    try:
                        if caminho_som not in self.sons: self.sons[caminho_som] = pygame.mixer.Sound(caminho_som)
                        self.sons[caminho_som].set_volume(max(0.0, min(1.0, vol)))
                        self.sons[caminho_som].play()
                    except: pass

                # ================= NOVO: SISTEMA DE SAVE (DATASTORE) =================
                elif comando == "SALVAR_DADOS":
                    # SALVAR_DADOS save.json chave valor
                    arquivo_save = partes[1]
                    chave = partes[2]
                    valor = self.variaveis.get(partes[3], partes[3]) if partes[3] in self.variaveis else partes[3]
                    dados = {}
                    if os.path.exists(arquivo_save):
                        try:
                            with open(arquivo_save, "r") as f: dados = json.load(f)
                        except: pass
                    dados[chave] = valor
                    with open(arquivo_save, "w") as f: json.dump(dados, f)

                elif comando == "CARREGAR_DADOS":
                    # CARREGAR_DADOS save.json chave variavel_destino
                    arquivo_save = partes[1]
                    chave = partes[2]
                    var_dest = partes[3]
                    if os.path.exists(arquivo_save):
                        try:
                            with open(arquivo_save, "r") as f:
                                dados = json.load(f)
                                if chave in dados:
                                    val = dados[chave]
                                    self.variaveis[var_dest] = float(val) if isinstance(val, (int, float)) else val
                        except: pass

                # ================= NOVO: SCREEN SHAKE =================
                elif comando == "CAMERA_TREMER":
                    # CAMERA_TREMER intensidade duracao_frames
                    self.shake_intensidade = float(partes[1])
                    self.shake_tempo = int(partes[2])

                elif comando == "CRIAR_TEXTO":
                    texto = re.findall(r'"([^"]*)"', linha)[0]
                    self.textos[partes[1]] = {
                        "fonte": pygame.font.SysFont("segoeui", int(partes[2]), bold=True),
                        "cor": (int(partes[5]), int(partes[6]), int(partes[7])),
                        "texto": texto, "pos": (int(partes[3]), int(partes[4]))
                    }

                elif comando == "ATUALIZAR_TEXTO":
                    if partes[1] in self.textos: self.textos[partes[1]]["texto"] = re.findall(r'"([^"]*)"', linha)[0]

                elif comando == "CRIAR_FUNDO":
                    try: self.fundo = pygame.transform.scale(pygame.image.load(self.formatar_caminho(partes[1])).convert(), (self.largura, self.altura))
                    except: pass

                elif comando == "CRIAR_SPRITE":
                    nome, caminho, x, y = partes[1], self.formatar_caminho(partes[2]), float(partes[3]), float(partes[4])
                    try: img = pygame.image.load(caminho).convert_alpha()
                    except: 
                        img = pygame.Surface((45, 45)); img.fill((0, 240, 255))
                    rect = img.get_rect(topleft=(int(x), int(y)))
                    self.sprites[nome] = {
                        "img": img, "rect": rect, "x": x, "y": y,
                        "vx": 0.0, "vy": 0.0, "ax": 0.0, "ay": 0.0,
                        "visivel": True,
                    }

                elif comando == "CRIAR_CUBO":
                    nome = partes[1]
                    x, y = float(partes[2]), float(partes[3])
                    larg, alt = int(partes[4]), int(partes[5])
                    cor = (int(partes[6]), int(partes[7]), int(partes[8]))
                    img = pygame.Surface((larg, alt))
                    img.fill(cor)
                    rect = img.get_rect(topleft=(int(x), int(y)))
                    self.sprites[nome] = {
                        "img": img, "rect": rect, "x": x, "y": y,
                        "vx": 0.0, "vy": 0.0, "ax": 0.0, "ay": 0.0,
                        "visivel": True,
                    }

                # NOVO: Mudar a cor de um cubo no meio do jogo
                elif comando == "DEFINIR_COR_SPRITE":
                    nome = partes[1]
                    if nome in self.sprites:
                        r, g, b = int(partes[2]), int(partes[3]), int(partes[4])
                        sp = self.sprites[nome]
                        sp["img"].fill((r, g, b))

                elif comando == "DEFINIR_FISICA":
                    nome = partes[1]
                    if nome in self.sprites:
                        self.sprites[nome]["vx"] = float(partes[2])
                        self.sprites[nome]["vy"] = float(partes[3])

                elif comando == "IMPULSAR_OBJETO":
                    nome = partes[1]
                    if nome in self.sprites:
                        self.sprites[nome]["vx"] += self.converter_numero(partes[2])
                        self.sprites[nome]["vy"] += self.converter_numero(partes[3])

                elif comando == "DEFINIR_ACELERACAO":
                    nome = partes[1]
                    if nome in self.sprites:
                        self.sprites[nome]["ax"] = self.converter_numero(partes[2])
                        self.sprites[nome]["ay"] = self.converter_numero(partes[3])

                elif comando == "DESLIZAR_ATE":
                    nome = partes[1]
                    velocidade = self.converter_numero(partes[4])
                    if nome in self.sprites:
                        if velocidade <= 0:
                            raise ValueError("DESLIZAR_ATE exige uma velocidade positiva.")
                        self.deslizamentos[nome] = {
                            "x": self.converter_numero(partes[2]),
                            "y": self.converter_numero(partes[3]),
                            "velocidade": velocidade,
                        }

                elif comando == "CACAR_ALVO":
                    nome, alvo = partes[1], partes[2]
                    velocidade = self.converter_numero(partes[3])
                    if nome in self.sprites and alvo in self.sprites:
                        if velocidade <= 0:
                            raise ValueError("CACAR_ALVO exige uma velocidade positiva.")
                        self.alvos[nome] = {"sprite": alvo, "velocidade": velocidade}

                elif comando == "PARAR_MOVIMENTO":
                    nome = partes[1]
                    self.deslizamentos.pop(nome, None)
                    self.alvos.pop(nome, None)

                elif comando == "REBATER_RAQUETE":
                    colidiu = self.rebater_raquete(partes[1], partes[2])
                    if colidiu and len(partes) > 3:
                        self.executar_bloco(partes[3], usar_delta=False)

                elif comando == "REBATER_TELA":
                    nome = partes[1]
                    if nome in self.sprites and self.sprites[nome]["visivel"]:
                        sp = self.sprites[nome]
                        larg_sp = sp["rect"].width
                        alt_sp = sp["rect"].height
                        
                        if sp["x"] <= 0:
                            self.sincronizar_pos(sp, 1.0, sp["y"])
                            sp["vx"] = abs(sp["vx"]) if sp["vx"] != 0 else 5.0
                        elif sp["x"] + larg_sp >= self.largura:
                            self.sincronizar_pos(sp, self.largura - larg_sp - 1.0, sp["y"])
                            sp["vx"] = -abs(sp["vx"]) if sp["vx"] != 0 else -5.0
                            
                        if sp["y"] <= 0:
                            self.sincronizar_pos(sp, sp["x"], 1.0)
                            sp["vy"] = abs(sp["vy"]) if sp["vy"] != 0 else 5.0
                        elif sp["y"] + alt_sp >= self.altura:
                            self.sincronizar_pos(sp, sp["x"], self.altura - alt_sp - 1.0)
                            sp["vy"] = -abs(sp["vy"]) if sp["vy"] != 0 else -5.0

                elif comando == "SE_TOCAR_BORDA":
                    nome_sprite = partes[1]
                    direcao = partes[2].lower()
                    cena_destino = partes[3]
                    
                    if nome_sprite in self.sprites and self.sprites[nome_sprite]["visivel"]:
                        sp = self.sprites[nome_sprite]
                        r = sp["rect"]
                        tocou = False
                        if direcao == "esquerda" and r.left <= 0: tocou = True
                        elif direcao == "direita" and r.right >= self.largura: tocou = True
                        elif direcao == "topo" and r.top <= 0: tocou = True
                        elif direcao == "baixo" and r.bottom >= self.altura: tocou = True
                        if tocou:
                            self.executar_bloco(cena_destino, usar_delta=False)

                elif comando == "REBATER_OBJETO":
                    nome1, nome2 = partes[1], partes[2]
                    cena_colisao = partes[3] if len(partes) > 3 else None
                    
                    if nome1 in self.sprites and nome2 in self.sprites:
                        s1, s2 = self.sprites[nome1], self.sprites[nome2]
                        if s1["visivel"] and s2["visivel"] and s1["rect"].colliderect(s2["rect"]):
                            r1, r2 = s1["rect"], s2["rect"]
                            dx = r1.centerx - r2.centerx
                            dy = r1.centery - r2.centery
                            
                            overlap_x = (r1.width / 2.0 + r2.width / 2.0) - abs(dx)
                            overlap_y = (r1.height / 2.0 + r2.height / 2.0) - abs(dy)
                            
                            if abs(overlap_x - overlap_y) < 4.0:
                                if dx > 0: s1["vx"] = abs(s1["vx"]); novo_x = r2.right + 2.0
                                else: s1["vx"] = -abs(s1["vx"]); novo_x = r2.left - r1.width - 2.0
                                    
                                if dy > 0: s1["vy"] = abs(s1["vy"]); novo_y = r2.bottom + 2.0
                                else: s1["vy"] = -abs(s1["vy"]); novo_y = r2.top - r1.height - 2.0
                                    
                                self.sincronizar_pos(s1, novo_x, novo_y)
                            elif overlap_x < overlap_y:
                                if dx > 0: self.sincronizar_pos(s1, r2.right + 2.0, s1["y"]); s1["vx"] = abs(s1["vx"])
                                else: self.sincronizar_pos(s1, r2.left - r1.width - 2.0, s1["y"]); s1["vx"] = -abs(s1["vx"])
                            else:
                                if dy > 0: self.sincronizar_pos(s1, s1["x"], r2.bottom + 2.0); s1["vy"] = abs(s1["vy"])
                                else: self.sincronizar_pos(s1, s1["x"], r2.top - r1.height - 2.0); s1["vy"] = -abs(s1["vy"])
                                    
                                if r2.width >= 80:
                                    fator_canto = (r1.centerx - r2.centerx) / (r2.width / 2.0)
                                    velocidade_base = max(abs(s1["vx"]), 6.0)
                                    if abs(fator_canto) > 0.35:
                                        s1["vx"] = velocidade_base * (1.0 if fator_canto > 0 else -1.0)
                                
                            if cena_colisao:
                                self.executar_bloco(cena_colisao, usar_delta=False)

                elif comando == "REBATER_TRAJETORIA":
                    nome1, nome2 = partes[1], partes[2]
                    cena_colisao = partes[3] if len(partes) > 3 else None
                    if self.rebater_trajetoria(nome1, nome2) and cena_colisao:
                        self.executar_bloco(cena_colisao, usar_delta=False)

                elif comando == "MOVER_ALEATORIO":
                    nome = partes[1]
                    if nome in self.sprites:
                        sp = self.sprites[nome]
                        nx = float(random.randint(int(partes[2]), int(partes[3])))
                        ny = float(random.randint(int(partes[4]), int(partes[5])))
                        self.sincronizar_pos(sp, nx, ny)
                        sp["prev_x"] = sp["x"]
                        sp["prev_y"] = sp["y"]

                elif comando == "OCULTAR_SPRITE":
                    if partes[1] in self.sprites: self.sprites[partes[1]]["visivel"] = False
                elif comando == "MOSTRAR_SPRITE":
                    if partes[1] in self.sprites: self.sprites[partes[1]]["visivel"] = True

                elif comando == "MOVER_PARA":
                    if partes[1] in self.sprites:
                        sp = self.sprites[partes[1]]
                        self.sincronizar_pos(sp, float(partes[2]), float(partes[3]))
                        sp["prev_x"] = sp["x"]
                        sp["prev_y"] = sp["y"]

                elif comando == "MOVER":
                    if partes[1] in self.sprites:
                        sp = self.sprites[partes[1]]
                        nx = sp["x"] + float(partes[2]) * escala
                        ny = sp["y"] + float(partes[3]) * escala
                        self.sincronizar_pos(sp, nx, ny)
                        
                elif comando == "LIMITAR_TELA":
                    if partes[1] in self.sprites:
                        sp = self.sprites[partes[1]]
                        larg_sp = sp["rect"].width
                        alt_sp = sp["rect"].height
                        nx, ny = sp["x"], sp["y"]
                        if nx < 0: nx = 0.0
                        elif nx + larg_sp > self.largura: nx = float(self.largura - larg_sp)
                        if ny < 0: ny = 0.0
                        elif ny + alt_sp > self.altura: ny = float(self.altura - alt_sp)
                        self.sincronizar_pos(sp, nx, ny)
                        
                elif comando == "SE_COLIDIR":
                    if partes[1] in self.sprites and partes[2] in self.sprites:
                        if self.sprites[partes[1]]["visivel"] and self.sprites[partes[2]]["visivel"]:
                            if self.sprites[partes[1]]["rect"].colliderect(self.sprites[partes[2]]["rect"]):
                                self.executar_bloco(partes[3], usar_delta=False)
                                
                elif comando == "DESTRUIR_SPRITE":
                    if partes[1] in self.sprites: del self.sprites[partes[1]]

                elif comando == "AO_SEGURAR_MOVER":
                    self.eventos_segurar_mover[partes[1].lower()] = {
                        "sprite": partes[2], "dx": float(partes[3]), "dy": float(partes[4])
                    }

                elif comando == "AO_TECLAR": self.eventos_tecla[partes[1].lower()] = partes[2]
                elif comando == "AO_SEGURAR": self.eventos_segurar[partes[1].lower()] = partes[2]
                elif comando == "AO_CLICAR": self.eventos_clique[partes[1]] = partes[2]
                elif comando == "SAIR": 
                    self.rodando = False
                    break

            except Exception as e:
                print(f"Aviso na linha '{linha}': {e}")
                
            linha_idx += 1

    def DesenharHudLunar(self, teclas):
        if self.config.get("mostrar_fps", True):
             bg_fps = pygame.Surface((110, 32), pygame.SRCALPHA)
             bg_fps.fill((0, 0, 0, 160))
             self.tela.blit(bg_fps, (self.largura - 120, 10))
             fps_txt = self.fonte_hud.render(f"[{int(self.clock.get_fps())} FPS]", True, (0, 240, 255))
             self.tela.blit(fps_txt, (self.largura - 108, 15))

        if self.config.get("keystrokes", True):
            mapa = [("W", pygame.K_w, 50, 480), ("A", pygame.K_a, 10, 520), 
                    ("S", pygame.K_s, 50, 520), ("D", pygame.K_d, 90, 520)]
            for letra, code, kx, ky in mapa:
                ativo = teclas[code]
                cor_box = (0, 240, 255, 200) if ativo else (0, 0, 0, 150)
                cor_txt = (10, 10, 15) if ativo else (255, 255, 255)
                
                box = pygame.Surface((36, 36), pygame.SRCALPHA)
                box.fill(cor_box)
                self.tela.blit(box, (kx, ky))
                txt = self.fonte_hud.render(letra, True, cor_txt)
                self.tela.blit(txt, (kx + 11, ky + 7))

    def rodar(self):
        try:
            self.executar_bloco("inicio", usar_delta=False)
            fps_alvo = self.config.get("fps", 60)
            modo_debug = self.config.get("modo_debug", False)
            tick_rate = 0 if fps_alvo == 0 else fps_alvo
            
            self.clock.tick(tick_rate)
            
            while self.rodando:
                dt = self.clock.tick(tick_rate) / 1000.0
                if dt > 0.05: dt = 0.05
                self.fator_fps = dt * 60.0
                
                # 1. CÁLCULO DE SCREEN SHAKE (TREMOR DE CÂMERA)
                ox, oy = 0, 0
                if self.shake_tempo > 0:
                    ox = random.uniform(-self.shake_intensidade, self.shake_intensidade)
                    oy = random.uniform(-self.shake_intensidade, self.shake_intensidade)
                    self.shake_tempo -= 1
                
                # Renderiza fundo no buffer temporário ou deslocado pelo shake
                superficie_buffer = pygame.Surface((self.largura, self.altura))
                if self.fundo: superficie_buffer.blit(self.fundo, (0, 0))
                else: superficie_buffer.fill(self.cor_fundo)
                
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT: 
                        self.rodando = False
                    if evento.type == pygame.KEYDOWN:
                        if evento.key == pygame.K_f:
                            self.alternar_tela_cheia()
                        elif evento.key == pygame.K_ESCAPE and self.tela_cheia:
                            self.definir_tela_cheia(False)
                        else:
                            n_tecla = pygame.key.name(evento.key)
                            if n_tecla in self.eventos_tecla:
                                self.executar_bloco(self.eventos_tecla[n_tecla], usar_delta=False)
                    if evento.type == pygame.MOUSEBUTTONDOWN:
                        pos = self.converter_posicao_mouse(pygame.mouse.get_pos())
                        for n_sprite, dados in self.sprites.items():
                            if dados["visivel"] and dados["rect"].collidepoint(pos):
                                if n_sprite in self.eventos_clique: 
                                    self.executar_bloco(self.eventos_clique[n_sprite], usar_delta=False)

                if not self.rodando: break

                teclas = pygame.key.get_pressed()
                for t_nome, c_dest in self.eventos_segurar.items():
                    try:
                        if teclas[pygame.key.key_code(t_nome)]: 
                            self.executar_bloco(c_dest, usar_delta=True)
                    except: pass

                for t_nome, dados in self.eventos_segurar_mover.items():
                    try:
                        if teclas[pygame.key.key_code(t_nome)]:
                            nome_sp = dados["sprite"]
                            if nome_sp in self.sprites and self.sprites[nome_sp]["visivel"]:
                                sp = self.sprites[nome_sp]
                                nx = sp["x"] + dados["dx"] * self.fator_fps
                                ny = sp["y"] + dados["dy"] * self.fator_fps
                                self.sincronizar_pos(sp, nx, ny)
                    except: pass

                for sp in self.sprites.values():
                    if sp["visivel"]:
                        sp["prev_x"] = sp["x"]
                        sp["prev_y"] = sp["y"]
                        sp["vx"] += sp.get("ax", 0.0) * self.fator_fps
                        sp["vy"] += sp.get("ay", 0.0) * self.fator_fps
                        if sp["vx"] != 0 or sp["vy"] != 0:
                            nx = sp["x"] + sp["vx"] * self.fator_fps
                            ny = sp["y"] + sp["vy"] * self.fator_fps
                            self.sincronizar_pos(sp, nx, ny)

                self.atualizar_movimentos_especiais()
                
                if "loop" in self.cenas: 
                    self.executar_bloco("loop", usar_delta=True)

                agora = pygame.time.get_ticks()
                for identificador, (prazo, nome_cena) in list(self.temporizadores.items()):
                    if agora >= prazo:
                        del self.temporizadores[identificador]
                        self.executar_bloco(nome_cena, usar_delta=False)
                
                # Desenha Sprites com suporte a Camera Shake
                for dados in self.sprites.values():
                    if dados["visivel"]: 
                        rect_ajustado = dados["rect"].copy()
                        rect_ajustado.x += int(ox)
                        rect_ajustado.y += int(oy)
                        superficie_buffer.blit(dados["img"], rect_ajustado)
                        if modo_debug:
                            pygame.draw.rect(superficie_buffer, (0, 240, 255), rect_ajustado, 2)
                    
                # Desenha Textos com suporte a Camera Shake
                for dados in self.textos.values():
                    texto_formatado = self.resolver_texto(dados["texto"])
                    surf = dados["fonte"].render(texto_formatado, True, dados["cor"])
                    px, py = dados["pos"]
                    superficie_buffer.blit(surf, (px + int(ox), py + int(oy)))
                
                # Mantém a proporção do jogo e usa toda a área disponível no fullscreen.
                tela_largura, tela_altura = self.tela.get_size()
                escala = min(tela_largura / self.largura, tela_altura / self.altura)
                destino_largura = max(1, round(self.largura * escala))
                destino_altura = max(1, round(self.altura * escala))
                if (destino_largura, destino_altura) == superficie_buffer.get_size():
                    superficie_saida = superficie_buffer
                else:
                    superficie_saida = pygame.transform.smoothscale(
                        superficie_buffer, (destino_largura, destino_altura)
                    )
                self.tela.fill((0, 0, 0))
                pos_x = (tela_largura - destino_largura) // 2
                pos_y = (tela_altura - destino_altura) // 2
                self.tela.blit(superficie_saida, (pos_x, pos_y))
                
                self.DesenharHudLunar(teclas)
                pygame.display.flip()
                
            pygame.quit()
                
        except Exception as e:
            pygame.quit()
            erro_formatado = traceback.format_exc()
            messagebox.showerror("Crash Report - UAL Client", f"Um erro interrompeu o jogo:\n\n{erro_formatado}")
        finally:
            if self._diretorio_temp is not None:
                self._diretorio_temp.cleanup()
                self._diretorio_temp = None
                self.pasta_temp = ""


# ==========================================
# JOGO DEMO 9.0: TESTE DE TELA CHEIA E SHAKE
# ==========================================
JOGO_ULTIMATE_DEMO = """# === JOGO ULTIMATE 9.0 ===
CENA inicio
DEFINIR_TELA 800 600
DEFINIR_FUNDO_COR 12 14 24

# Tenta carregar highscore salvo anteriormente
CARREGAR_DADOS recorde.json maior_pontos recorde_salvo

VAR_CRIAR pontos 0
VAR_CRIAR recorde_salvo 0

CRIAR_CUBO player 375 500 50 50 0 240 255
CRIAR_CUBO inimigo 380 50 40 40 255 50 90

DEFINIR_FISICA inimigo 5 4

CRIAR_TEXTO hud_pts 22 20 15 0 240 255 "PONTOS: {pontos}"
CRIAR_TEXTO hud_rec 22 20 45 255 215 0 "RECORDE: {recorde_salvo}"
CRIAR_TEXTO ajuda 16 20 560 140 150 180 "[F] Tela cheia | [ESC] Voltar | [W A S D] Move o Cubo"

AO_SEGURAR_MOVER w player 0 -8
AO_SEGURAR_MOVER s player 0 8
AO_SEGURAR_MOVER a player -8 0
AO_SEGURAR_MOVER d player 8 0

AO_TECLAR r salvar_pontuacao
FIM_CENA

CENA loop
LIMITAR_TELA player
REBATER_TELA inimigo
REBATER_OBJETO inimigo player bateu_no_player
VAR_SOMA pontos 1
ATUALIZAR_TEXTO hud_pts "PONTOS: {pontos}"
FIM_CENA

CENA bateu_no_player
# TREME A CÂMERA COM INTENSIDADE 12 DURANTE 20 FRAMES!
CAMERA_TREMER 12 20
DEFINIR_COR_SPRITE player 255 0 0
FIM_CENA

CENA salvar_pontuacao
SALVAR_DADOS recorde.json maior_pontos pontos
ATUALIZAR_TEXTO hud_rec "RECORDE: {pontos}"
FIM_CENA
"""


# ==========================================
# LUNAR CLIENT STYLE LAUNCHER (COM TELA CHEIA)
# ==========================================
class RoundedButton(tk.Canvas):
    def __init__(
        self, parent, text, command, width=160, height=42,
        background="#202738", foreground="#ffffff",
        hover_background="#303c52", disabled_background="#20242d",
        disabled_foreground="#737b8b", font=("Segoe UI", 10, "bold"),
    ):
        super().__init__(
            parent, width=width, height=height,
            bg=parent.cget("bg"), highlightthickness=0, bd=0,
        )
        self.text = text
        self.command = command
        self.background = background
        self.foreground = foreground
        self.hover_background = hover_background
        self.disabled_background = disabled_background
        self.disabled_foreground = disabled_foreground
        self.font = font
        self.enabled = True
        self.hovered = False
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self._draw()

    def _rounded_points(self, width, height, radius):
        points = []
        for center_x, center_y, start in (
            (radius, radius, 180),
            (width - radius, radius, 270),
            (width - radius, height - radius, 0),
            (radius, height - radius, 90),
        ):
            for step in range(7):
                angle = math.radians(start + step * 15)
                points.extend((
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                ))
        return points

    def _draw(self, _event=None):
        self.delete("all")
        width = max(self.winfo_width(), int(self.cget("width")))
        height = max(self.winfo_height(), int(self.cget("height")))
        fill = self.background
        color = self.foreground
        if not self.enabled:
            fill, color = self.disabled_background, self.disabled_foreground
        elif self.hovered:
            fill = self.hover_background
        inset = 1
        self.create_polygon(
            self._rounded_points(width - inset * 2, height - inset * 2, 12),
            fill=fill, outline=fill, smooth=True,
        )
        self.create_text(
            width / 2, height / 2, text=self.text,
            fill=color, font=self.font,
        )

    def _enter(self, _event=None):
        self.hovered = True
        self._draw()

    def _leave(self, _event=None):
        self.hovered = False
        self._draw()

    def _click(self, _event=None):
        if self.enabled and self.command is not None:
            self.command()

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.configure(cursor="hand2" if self.enabled else "arrow")
        self._draw()

    def set_text(self, text):
        self.text = text
        self._draw()


class LunarLauncherUAL:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UAL Game Hub")
        self.root.geometry("1160x740")
        self.root.configure(bg="#090d18")
        self.root.resizable(False, False)
        self.root.withdraw()
        
        self.c_bg = "#090d18"
        self.c_sidebar = "#101827"
        self.c_card = "#151e30"
        self.c_card_hover = "#1b2940"
        self.c_border = "#293a57"
        self.c_accent = "#42e8ff"
        self.c_green = "#62f6b5"
        self.c_pink = "#ff5c93"
        self.c_text = "#f4f8ff"
        self.c_sub = "#91a0ba"
        
        self.var_fps = tk.StringVar(value="Ilimitado")
        self.var_fullscreen = tk.BooleanVar(value=False)
        self.var_show_fps = tk.BooleanVar(value=True)
        self.var_keystrokes = tk.BooleanVar(value=True)
        self.var_debug = tk.BooleanVar(value=False)
        self.jogos_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "jogos"
        )
        os.makedirs(self.jogos_dir, exist_ok=True)
        self.store_api_url = (
            "https://api.github.com/repos/tarcisioferraz/laucher/"
            "contents/jogos?ref=main"
        )
        self.store_raw_prefix = (
            "https://raw.githubusercontent.com/tarcisioferraz/laucher/main/jogos/"
        )
        self.biblioteca = []
        self.jogo_selecionado = None
        self.catalogo_loja = []
        self.busca_loja = tk.StringVar()
        self.pagina_atual = "biblioteca"
        self.carregando_loja = False
        self.downloads_em_andamento = set()
        self.fila_background = queue.Queue()
        self.poll_background_ativo = False
        self.tela_carregamento = None
        self.titulo_carregamento = None
        self.descricao_carregamento = None
        self.configurar_estilos()
        
        self.mostrar_tela_carregamento(
            "INICIANDO O UAL GAME HUB",
            "Preparando sua biblioteca de jogos...",
        )
        self.root.after(650, self._concluir_inicio)

    def configurar_estilos(self):
        estilo = ttk.Style(self.root)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure(
            "TCombobox", fieldbackground=self.c_card, background=self.c_card,
            foreground=self.c_text, arrowcolor=self.c_accent,
            bordercolor=self.c_border, lightcolor=self.c_border,
        )
        estilo.map(
            "TCombobox", fieldbackground=[("readonly", self.c_card)],
            selectbackground=[("readonly", self.c_card_hover)],
            selectforeground=[("readonly", self.c_text)],
        )
        estilo.configure(
            "Horizontal.TScrollbar", background=self.c_card_hover,
            troughcolor=self.c_bg, bordercolor=self.c_bg, arrowcolor=self.c_accent,
        )
        estilo.configure(
            "Vertical.TScrollbar", background=self.c_card_hover,
            troughcolor=self.c_bg, bordercolor=self.c_bg, arrowcolor=self.c_accent,
        )
        estilo.configure(
            "Horizontal.TProgressbar", troughcolor="#0c1423", background=self.c_accent,
            bordercolor="#0c1423", lightcolor=self.c_accent, darkcolor=self.c_accent,
        )

    def mostrar_tela_carregamento(self, titulo, descricao):
        """Exibe uma tela leve enquanto o launcher ou um jogo é preparado."""
        if self.tela_carregamento is not None and self.tela_carregamento.winfo_exists():
            self.titulo_carregamento.config(text=titulo)
            self.descricao_carregamento.config(text=descricao)
            self.tela_carregamento.deiconify()
            self.tela_carregamento.lift()
            self.tela_carregamento.update_idletasks()
            return

        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.configure(bg=self.c_bg)
        splash.attributes("-topmost", True)
        largura, altura = 460, 250
        x = (splash.winfo_screenwidth() - largura) // 2
        y = (splash.winfo_screenheight() - altura) // 2
        splash.geometry(f"{largura}x{altura}+{x}+{y}")

        painel = tk.Frame(
            splash, bg="#12141c", highlightthickness=1,
            highlightbackground="#293247",
        )
        painel.pack(fill="both", expand=True, padx=2, pady=2)
        tk.Label(painel, text="UAL", font=("Segoe UI", 31, "bold"),
                 bg="#12141c", fg=self.c_accent).pack(pady=(48, 5))
        self.titulo_carregamento = tk.Label(
            painel, text=titulo, font=("Segoe UI", 12, "bold"),
            bg="#12141c", fg=self.c_text,
        )
        self.titulo_carregamento.pack()
        self.descricao_carregamento = tk.Label(
            painel, text=descricao, font=("Segoe UI", 9),
            bg="#12141c", fg=self.c_sub,
        )
        self.descricao_carregamento.pack(pady=(6, 18))
        progresso = ttk.Progressbar(painel, mode="indeterminate", length=260)
        progresso.pack()
        progresso.start(12)
        self.tela_carregamento = splash
        splash.update_idletasks()

    def fechar_tela_carregamento(self):
        if self.tela_carregamento is not None and self.tela_carregamento.winfo_exists():
            self.tela_carregamento.destroy()
        self.tela_carregamento = None

    def _concluir_inicio(self):
        self.montar_ui()
        self.fechar_tela_carregamento()
        self.root.deiconify()

    def fechar_launcher(self):
        if messagebox.askyesno(
            "Fechar UAL Game Hub",
            "Deseja desligar o launcher Python?",
            parent=self.root,
        ):
            self.fechar_tela_carregamento()
            self.root.destroy()

    def ativar_modo_repouso(self):
        """Mantém o launcher aberto, mas o minimiza para a barra de tarefas."""
        self.root.iconify()
        
    def montar_ui(self):
        topo = tk.Frame(self.root, bg=self.c_bg, height=68)
        topo.pack(fill="x", padx=28, pady=(8, 0))
        topo.pack_propagate(False)
        marca = tk.Frame(topo, bg=self.c_bg)
        marca.pack(side="left", anchor="center")
        tk.Frame(marca, bg=self.c_accent, width=4, height=35).pack(
            side="left", padx=(0, 10), pady=8,
        )
        tk.Label(marca, text="UAL", font=("Segoe UI", 23, "bold"),
                 bg=self.c_bg, fg=self.c_text).pack(side="left")
        tk.Label(marca, text="GAME HUB", font=("Segoe UI", 9, "bold"),
                 bg=self.c_bg, fg=self.c_accent).pack(side="left", padx=(8, 0), pady=(8, 0))
        tk.Label(topo, text="●  PRONTO PARA JOGAR", font=("Segoe UI", 8, "bold"),
                 bg="#102a2f", fg=self.c_green, padx=10, pady=5).pack(
            side="left", padx=20,
        )
        self.botao_configuracoes = RoundedButton(
            topo, "⚙", self.alternar_configuracoes,
            width=44, height=42, background=self.c_card,
            hover_background=self.c_card_hover, font=("Segoe UI Symbol", 17),
        )
        self.botao_configuracoes.pack(side="right", anchor="center")
        RoundedButton(
            topo, "⏾  DESLIGAR", self.fechar_launcher,
            width=125, height=42, background="#4a2334", foreground="#ffffff",
            hover_background="#713149", font=("Segoe UI", 9, "bold"),
        ).pack(side="right", anchor="center", padx=(0, 9))
        RoundedButton(
            topo, "☾  REPOUSO", self.ativar_modo_repouso,
            width=125, height=42, background="#233353", foreground="#ffffff",
            hover_background="#314a78", font=("Segoe UI", 9, "bold"),
        ).pack(side="right", anchor="center", padx=(0, 9))

        self.main_area = tk.Frame(self.root, bg=self.c_bg)
        self.main_area.pack(fill="both", expand=True, padx=25, pady=(3, 17))
        
        self.construir_aba_play()
        self.construir_aba_loja()
        self.construir_aba_mods()
        self.configurar_rolagem_mouse()
        
        self.trocar_aba(self.aba_play, "biblioteca")

    def configurar_rolagem_mouse(self):
        """Permite rolar as páginas mesmo com o cursor sobre os cards."""
        self.root.bind_all("<MouseWheel>", self.rolar_pagina_com_mouse, add="+")
        # Compatibilidade para sistemas que enviam eventos de botão em vez de delta.
        self.root.bind_all("<Button-4>", self.rolar_pagina_com_mouse, add="+")
        self.root.bind_all("<Button-5>", self.rolar_pagina_com_mouse, add="+")

    def rolar_pagina_com_mouse(self, evento):
        if hasattr(evento, "delta") and evento.delta:
            passos = -1 if evento.delta > 0 else 1
        elif getattr(evento, "num", None) == 4:
            passos = -1
        else:
            passos = 1

        if self.pagina_atual == "biblioteca":
            # Os cards da biblioteca ficam lado a lado.
            self.galeria_canvas.xview_scroll(passos, "units")
            return "break"
        if self.pagina_atual == "loja":
            self.loja_canvas.yview_scroll(passos, "units")
            return "break"

    def criar_navegacao(self, parent, pagina_ativa):
        barra = tk.Frame(parent, bg=self.c_bg)
        barra.pack(fill="x", pady=(12, 2))
        RoundedButton(
            barra, "▣   MINHA BIBLIOTECA",
            lambda: self.trocar_aba(self.aba_play, "biblioteca"),
            width=205,
            background=self.c_accent if pagina_ativa == "biblioteca" else self.c_card,
            foreground="#06131b" if pagina_ativa == "biblioteca" else self.c_text,
            hover_background="#56f4ff" if pagina_ativa == "biblioteca" else "#303c52",
        ).pack(side="left", padx=(0, 10))
        RoundedButton(
            barra, "✦   LOJA DE JOGOS",
            lambda: self.abrir_loja(),
            width=180,
            background=self.c_accent if pagina_ativa == "loja" else self.c_card,
            foreground="#06131b" if pagina_ativa == "loja" else self.c_text,
            hover_background="#56f4ff" if pagina_ativa == "loja" else "#303c52",
        ).pack(side="left")
        tk.Label(
            barra, text="● ONLINE" if self.catalogo_loja else "UAL GAME HUB",
            font=("Segoe UI", 8, "bold"), bg=self.c_bg, fg=self.c_green,
        ).pack(side="right", padx=8)

    def trocar_aba(self, aba_destino, pagina=None):
        for aba in (self.aba_play, self.aba_loja, self.aba_mods):
            aba.pack_forget()
        aba_destino.pack(fill="both", expand=True)
        if pagina:
            self.pagina_atual = pagina

    def alternar_configuracoes(self):
        if self.pagina_atual == "configuracoes":
            self.trocar_aba(self.aba_play, "biblioteca")
        else:
            self.trocar_aba(self.aba_mods, "configuracoes")

    def abrir_loja(self):
        self.trocar_aba(self.aba_loja, "loja")
        if not self.catalogo_loja and not self.carregando_loja:
            self.carregar_catalogo_loja()

    def obter_configs(self):
        fps_str = self.var_fps.get()
        fps_val = 0 if "Ilimitado" in fps_str else int(fps_str.split()[0])
        return {
            "fps": fps_val,
            "fullscreen": self.var_fullscreen.get(),
            "mostrar_fps": self.var_show_fps.get(),
            "keystrokes": self.var_keystrokes.get(),
            "modo_debug": self.var_debug.get()
        }

    def construir_aba_play(self):
        self.aba_play = tk.Frame(self.main_area, bg=self.c_bg)
        topo = tk.Frame(self.aba_play, bg=self.c_bg)
        topo.pack(fill="x", pady=(13, 12))
        f_titulos = tk.Frame(topo, bg=self.c_bg)
        f_titulos.pack(side="left")
        tk.Label(f_titulos, text="MINHA BIBLIOTECA", font=("Segoe UI", 22, "bold"),
                 bg=self.c_bg, fg=self.c_text).pack(anchor="w")
        tk.Label(f_titulos, text="Seus jogos, prontos para continuar de onde parou",
                 font=("Segoe UI", 10), bg=self.c_bg, fg=self.c_sub).pack(anchor="w")

        destaque = tk.Frame(self.aba_play, bg="#111c30", height=190,
                            highlightthickness=1, highlightbackground=self.c_border)
        destaque.pack(fill="x", pady=(0, 17))
        destaque.pack_propagate(False)
        faixa_destaque = tk.Frame(destaque, bg=self.c_accent, width=5)
        faixa_destaque.pack(side="left", fill="y")
        faixa_destaque.pack_propagate(False)
        self.capa_destaque = tk.Label(destaque, bg="#0d1627")
        self.capa_destaque.pack(side="left", padx=18, pady=18)
        detalhes = tk.Frame(destaque, bg="#111c30")
        detalhes.pack(side="left", fill="both", expand=True, padx=(5, 16), pady=20)
        tk.Label(detalhes, text="CONTINUE JOGANDO", font=("Segoe UI", 9, "bold"),
                 bg="#111c30", fg=self.c_accent).pack(anchor="w")
        self.titulo_destaque = tk.Label(detalhes, text="", font=("Segoe UI", 20, "bold"),
                                        bg="#111c30", fg=self.c_text)
        self.titulo_destaque.pack(anchor="w", pady=(5, 2))
        self.subtitulo_destaque = tk.Label(
            detalhes, text="", font=("Segoe UI", 9), bg="#111c30",
            fg=self.c_sub, wraplength=570, justify="left",
        )
        self.subtitulo_destaque.pack(anchor="w", pady=(0, 6))
        self.botao_jogar = RoundedButton(
            detalhes, "▶   JOGAR AGORA", self.rodar_jogo_selecionado,
            width=190, background=self.c_green, foreground="#07150c",
            hover_background="#62ffae",
        )
        self.botao_jogar.pack(anchor="w", pady=(13, 0))

        linha_biblioteca = tk.Frame(self.aba_play, bg=self.c_bg)
        linha_biblioteca.pack(fill="x", pady=(0, 8))
        tk.Label(linha_biblioteca, text="SEUS JOGOS", font=("Segoe UI", 12, "bold"),
                 bg=self.c_bg, fg=self.c_text).pack(side="left")
        tk.Label(linha_biblioteca, text="Use a rodinha do mouse para navegar",
                 font=("Segoe UI", 8), bg=self.c_bg, fg=self.c_sub).pack(side="right")
        self.contagem_jogos = tk.Label(linha_biblioteca, text="", font=("Segoe UI", 9),
                                       bg=self.c_bg, fg=self.c_sub)
        self.contagem_jogos.pack(side="right")

        moldura_grade = tk.Frame(self.aba_play, bg=self.c_bg)
        moldura_grade.pack(fill="both", expand=True)
        self.galeria_canvas = tk.Canvas(moldura_grade, bg=self.c_bg, height=200,
                                        highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(moldura_grade, orient="horizontal",
                              command=self.galeria_canvas.xview)
        self.galeria_canvas.configure(xscrollcommand=barra.set)
        self.galeria_canvas.pack(fill="both", expand=True)
        barra.pack(fill="x", pady=(4, 0))
        self.galeria_conteudo = tk.Frame(self.galeria_canvas, bg=self.c_bg)
        self.galeria_canvas.create_window((0, 0), window=self.galeria_conteudo, anchor="nw")
        self.galeria_conteudo.bind(
            "<Configure>",
            lambda _: self.galeria_canvas.configure(
                scrollregion=self.galeria_canvas.bbox("all")
            ),
        )

        self.criar_navegacao(self.aba_play, "biblioteca")
        self.atualizar_biblioteca()

    def atualizar_biblioteca(self):
        demo = {"nome": "Demo UAL", "caminho": None, "demo": True}
        jogos = []
        for nome_arquivo in sorted(os.listdir(self.jogos_dir), key=str.casefold):
            caminho = os.path.join(self.jogos_dir, nome_arquivo)
            if os.path.isfile(caminho) and nome_arquivo.lower().endswith(".ual"):
                jogos.append({
                    "nome": os.path.splitext(nome_arquivo)[0],
                    "caminho": caminho,
                    "demo": False,
                    "arquivo": nome_arquivo,
                    "descricao": self._descricao_pacote(caminho),
                })
        self.biblioteca = [demo] + jogos
        if self.jogo_selecionado is None or not self.jogo_selecionado.get("demo"):
            selecionado = next(
                (jogo for jogo in jogos
                 if self.jogo_selecionado and
                 jogo["caminho"] == self.jogo_selecionado.get("caminho")),
                None,
            )
            self.jogo_selecionado = selecionado or (jogos[0] if jogos else demo)
        self.contagem_jogos.config(
            text=f"{len(jogos)} jogo(s) instalado(s)  •  Demo incluída"
        )
        for filho in self.galeria_conteudo.winfo_children():
            filho.destroy()
        for jogo in self.biblioteca:
            self._criar_card_jogo(jogo)
        self.atualizar_jogo_destaque()

    def _descricao_pacote(self, caminho):
        try:
            with zipfile.ZipFile(caminho) as pacote:
                leia_me = next(
                    (
                        membro for membro in pacote.namelist()
                        if os.path.basename(membro).casefold()
                        in ("leia-me.txt", "readme.txt", "readme.md")
                    ),
                    None,
                )
                if leia_me is None:
                    return "Jogo pronto para jogar."
                conteudo = pacote.read(leia_me).decode("utf-8-sig", errors="replace")
                linhas = [
                    linha.strip(" #=-\t")
                    for linha in conteudo.splitlines()
                    if linha.strip(" #=-\t")
                ]
                descricao = next(
                    (
                        linha for linha in linhas
                        if len(linha) > 35 and not linha.isupper()
                    ),
                    next((linha for linha in linhas if len(linha) > 12), ""),
                )
                if descricao:
                    return descricao[:180]
        except (OSError, zipfile.BadZipFile, RuntimeError):
            return "Jogo UAL instalado."
        return "Jogo pronto para jogar."

    def _imagem_capa_jogo(self, jogo):
        if "imagem_tk" in jogo:
            return jogo["imagem_tk"]

        largura, altura = 180, 102
        superficie = None
        if not jogo["demo"]:
            nome_base = os.path.splitext(jogo["arquivo"])[0].casefold()
            nomes_capa = {nome_base, f"{nome_base}_capa"}
            for nome_arquivo in os.listdir(self.jogos_dir):
                base, extensao = os.path.splitext(nome_arquivo)
                if base.casefold() in nomes_capa and extensao.lower() in (
                    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"
                ):
                    try:
                        superficie = pygame.image.load(
                            os.path.join(self.jogos_dir, nome_arquivo)
                        )
                    except pygame.error:
                        superficie = None
                    if superficie is not None:
                        break
            if superficie is None:
                superficie = self._imagem_pacote(jogo)

        if superficie is None:
            pygame.font.init()
            superficie = pygame.Surface((largura, altura))
            nome_lower = jogo["nome"].casefold()
            cor = (
                (20, 34, 58) if jogo["demo"]
                else (20, 50, 74) if "cosmic" in nome_lower or "breaker" in nome_lower
                else (36, 24, 70)
            )
            superficie.fill(cor)
            pygame.draw.circle(superficie, (0, 210, 230), (142, 30), 32, 2)
            pygame.draw.circle(superficie, (243, 63, 97), (155, 67), 21, 3)
            pygame.draw.polygon(superficie, (27, 45, 73), [
                (0, 102), (40, 70), (68, 84), (104, 46), (144, 85), (180, 57), (180, 102),
            ])
            pygame.draw.line(superficie, (0, 210, 230), (8, 11), (68, 11), 2)
            pygame.draw.line(superficie, (243, 63, 97), (8, 16), (42, 16), 2)
            fonte = pygame.font.SysFont("segoeui", 12, bold=True)
            titulo = fonte.render(jogo["nome"][:23], True, (245, 248, 255))
            superficie.blit(titulo, (9, 80))
        superficie = pygame.transform.smoothscale(superficie, (largura, altura))
        ppm = b"P6\n180 102\n255\n" + pygame.image.tostring(superficie, "RGB")
        jogo["imagem_tk"] = tk.PhotoImage(
            master=self.root, data=ppm, format="PPM"
        )
        return jogo["imagem_tk"]

    def _imagem_pacote(self, jogo):
        try:
            with zipfile.ZipFile(jogo["caminho"]) as pacote:
                imagens = [
                    nome for nome in pacote.namelist()
                    if os.path.splitext(nome)[1].casefold()
                    in (".png", ".jpg", ".jpeg", ".bmp")
                ]
                imagens.sort(key=lambda nome: (
                    os.path.basename(nome).casefold()
                    not in ("capa.png", "cover.png", "fundo.png", "background.png"),
                    len(nome),
                ))
                if imagens:
                    return pygame.image.load(
                        io.BytesIO(pacote.read(imagens[0]))
                    )
        except (OSError, zipfile.BadZipFile, pygame.error, RuntimeError):
            return None
        return None

    def _criar_card_jogo(self, jogo):
        selecionado = jogo is self.jogo_selecionado
        cor_borda = self.c_accent if selecionado else self.c_border
        cor_card = self.c_card_hover if selecionado else self.c_card
        card = tk.Frame(
            self.galeria_conteudo, bg=cor_card, width=210, height=188,
            highlightthickness=3 if selecionado else 1, highlightbackground=cor_borda,
        )
        card.pack(side="left", padx=(0, 14), pady=4)
        card.pack_propagate(False)
        capa = tk.Label(card, image=self._imagem_capa_jogo(jogo), bg=cor_card)
        capa.pack(padx=10, pady=(10, 7))
        nome = tk.Label(card, text=jogo["nome"], font=("Segoe UI", 10, "bold"),
                        bg=cor_card, fg=self.c_text, anchor="w")
        nome.pack(fill="x", padx=11)
        tipo = "JOGO UAL" if not jogo["demo"] else "EXPERIÊNCIA DE DEMO"
        tk.Label(card, text=("●  SELECIONADO" if selecionado else tipo),
                 font=("Segoe UI", 8, "bold"), bg=cor_card,
                 fg=self.c_accent if selecionado else self.c_sub,
                 anchor="w").pack(fill="x", padx=11, pady=(3, 0))

        def selecionar(_=None, item=jogo):
            self.jogo_selecionado = item
            self.atualizar_biblioteca()

        def vincular_clique(widget):
            widget.bind("<Button-1>", selecionar)
            for filho in widget.winfo_children():
                vincular_clique(filho)

        vincular_clique(card)

    def atualizar_jogo_destaque(self):
        jogo = self.jogo_selecionado
        if jogo is None:
            return
        self.capa_destaque.config(image=self._imagem_capa_jogo(jogo))
        self.titulo_destaque.config(text=jogo["nome"])
        descricao = jogo.get("descricao", "Uma demonstração para experimentar o motor UAL")
        self.subtitulo_destaque.config(text=descricao)

    def rodar_jogo_selecionado(self):
        jogo = self.jogo_selecionado
        if jogo is None:
            return
        nome_jogo = jogo["nome"]
        self.mostrar_tela_carregamento(
            "ABRINDO O JOGO",
            f"Carregando {nome_jogo}...",
        )
        self.root.withdraw()
        self.tela_carregamento.update()
        self.botao_jogar.set_enabled(False)
        # Devolve o controle ao Tk antes de abrir o Pygame. Isso garante que
        # a tela de carregamento seja desenhada e fique visível.
        self.root.after(300, lambda: self._iniciar_jogo(jogo))

    def _iniciar_jogo(self, jogo):
        nome_jogo = jogo["nome"]
        try:
            if jogo["demo"]:
                motor = MotorUalGrafico(
                    config=self.obter_configs(), codigo_puro=JOGO_ULTIMATE_DEMO
                )
            else:
                motor = MotorUalGrafico(
                    config=self.obter_configs(), caminho_arquivo_ual=jogo["caminho"]
                )
            # O Pygame já criou a janela: a tela de abertura não deve ficar
            # sobre o jogo enquanto ele está sendo jogado.
            self.fechar_tela_carregamento()
            motor.rodar()
        except Exception as erro:
            messagebox.showerror("Não foi possível iniciar o jogo", str(erro))
        finally:
            self.mostrar_tela_carregamento(
                "FECHANDO O JOGO",
                f"Salvando a sessão de {nome_jogo}...",
            )
            self.tela_carregamento.update()
            self.root.after(550, self._retornar_ao_launcher)

    def _retornar_ao_launcher(self):
        self.fechar_tela_carregamento()
        self.root.deiconify()
        self.botao_jogar.set_enabled(True)

    def construir_aba_loja(self):
        self.aba_loja = tk.Frame(self.main_area, bg=self.c_bg)
        topo = tk.Frame(self.aba_loja, bg=self.c_bg)
        topo.pack(fill="x", pady=(13, 12))
        tk.Label(topo, text="LOJA DE JOGOS", font=("Segoe UI", 22, "bold"),
                 bg=self.c_bg, fg=self.c_text).pack(anchor="w")
        tk.Label(topo, text="Descubra jogos UAL da comunidade e instale com um toque",
                 font=("Segoe UI", 10), bg=self.c_bg, fg=self.c_sub).pack(anchor="w")
        tk.Label(
            topo, text="Descrições opcionais: jogos/catalogo.json no GitHub",
            font=("Segoe UI", 8), bg=self.c_bg, fg=self.c_sub,
        ).pack(anchor="w", pady=(2, 0))

        barra_busca = tk.Frame(
            self.aba_loja, bg=self.c_card, padx=14, pady=9,
            highlightthickness=1, highlightbackground=self.c_border,
        )
        barra_busca.pack(fill="x", pady=(0, 10))
        tk.Label(barra_busca, text="⌕", font=("Segoe UI", 18),
                 bg=self.c_card, fg=self.c_accent).pack(side="left", padx=(0, 9))
        campo_busca = tk.Entry(
            barra_busca, textvariable=self.busca_loja, relief="flat",
            bg=self.c_card, fg=self.c_text, insertbackground=self.c_text,
            font=("Segoe UI", 11),
        )
        campo_busca.pack(side="left", fill="x", expand=True)
        campo_busca.insert(0, "")
        self.busca_loja.trace_add("write", lambda *_: self.mostrar_jogos_loja())

        self.loja_status = tk.Label(
            self.aba_loja, text="Conectando à loja do GitHub...",
            font=("Segoe UI", 9), bg=self.c_bg, fg=self.c_sub, anchor="w",
        )
        self.loja_status.pack(fill="x", pady=(0, 7))

        area = tk.Frame(self.aba_loja, bg=self.c_bg)
        area.pack(fill="both", expand=True)
        self.loja_canvas = tk.Canvas(
            area, bg=self.c_bg, highlightthickness=0, bd=0,
        )
        barra_vertical = ttk.Scrollbar(
            area, orient="vertical", command=self.loja_canvas.yview,
        )
        self.loja_canvas.configure(yscrollcommand=barra_vertical.set)
        barra_vertical.pack(side="right", fill="y")
        self.loja_canvas.pack(side="left", fill="both", expand=True)
        self.loja_conteudo = tk.Frame(self.loja_canvas, bg=self.c_bg)
        self.loja_window = self.loja_canvas.create_window(
            (0, 0), window=self.loja_conteudo, anchor="nw",
        )
        self.loja_conteudo.bind(
            "<Configure>",
            lambda _: self.loja_canvas.configure(
                scrollregion=self.loja_canvas.bbox("all")
            ),
        )
        self.loja_canvas.bind(
            "<Configure>",
            lambda evento: self.loja_canvas.itemconfigure(
                self.loja_window, width=evento.width
            ),
        )
        self.criar_navegacao(self.aba_loja, "loja")
        self.mostrar_jogos_loja()

    def carregar_catalogo_loja(self):
        if self.carregando_loja:
            return
        self.carregando_loja = True
        self.loja_status.config(text="Buscando jogos no GitHub...")
        self._ativar_poll_background()
        threading.Thread(
            target=self._buscar_catalogo_loja, daemon=True,
        ).start()

    def _ativar_poll_background(self):
        if not self.poll_background_ativo:
            self.poll_background_ativo = True
            self.root.after(100, self._processar_fila_background)

    def _processar_fila_background(self):
        while True:
            try:
                tipo, *dados = self.fila_background.get_nowait()
            except queue.Empty:
                break
            if tipo == "catalogo":
                self._catalogo_carregado(*dados)
            elif tipo == "download":
                self._download_concluido(*dados)
        if self.carregando_loja or self.downloads_em_andamento:
            self.root.after(100, self._processar_fila_background)
        else:
            self.poll_background_ativo = False

    def _buscar_catalogo_loja(self):
        try:
            requisicao = urllib.request.Request(
                self.store_api_url,
                headers={"User-Agent": "UAL-Game-Hub"},
            )
            with urllib.request.urlopen(requisicao, timeout=15) as resposta:
                conteudo = resposta.read(2_000_001)
            if len(conteudo) > 2_000_000:
                raise ValueError("A lista de jogos do GitHub é muito grande.")
            itens_github = json.loads(conteudo.decode("utf-8"))
            if not isinstance(itens_github, list):
                raise ValueError("O GitHub retornou uma lista de jogos inválida.")

            catalogo = {}
            for item in itens_github:
                if item.get("name", "").casefold() not in (
                    "catalogo.json", "catalog.json"
                ):
                    continue
                url_catalogo = item.get("download_url", "")
                if not url_catalogo.startswith(self.store_raw_prefix):
                    raise ValueError("O endereço do catálogo no GitHub é inválido.")
                requisicao_catalogo = urllib.request.Request(
                    url_catalogo, headers={"User-Agent": "UAL-Game-Hub"},
                )
                with urllib.request.urlopen(requisicao_catalogo, timeout=15) as resposta:
                    dados_catalogo = resposta.read(1_000_001)
                if len(dados_catalogo) > 1_000_000:
                    raise ValueError("O catálogo de descrições é muito grande.")
                catalogo = json.loads(dados_catalogo.decode("utf-8"))
                if not isinstance(catalogo, dict):
                    raise ValueError("O catálogo de descrições precisa ser um objeto JSON.")
                catalogo = catalogo.get("jogos", catalogo.get("games", catalogo))
                break

            jogos = []
            for item in itens_github:
                nome_arquivo = item.get("name", "")
                if (
                    item.get("type") != "file"
                    or not nome_arquivo.lower().endswith(".ual")
                    or os.path.basename(nome_arquivo) != nome_arquivo
                    or "\\" in nome_arquivo
                ):
                    continue
                url_download = item.get("download_url", "")
                if not url_download.startswith(self.store_raw_prefix):
                    raise ValueError(f"Endereço de download inválido para {nome_arquivo}.")
                metadados = catalogo.get(nome_arquivo, {})
                if not isinstance(metadados, dict):
                    metadados = {"descricao": str(metadados)}
                nome = (
                    metadados.get("titulo") or metadados.get("title")
                    or os.path.splitext(nome_arquivo)[0].replace("_", " ")
                )
                descricao = (
                    metadados.get("descricao") or metadados.get("description")
                    or "Jogo da comunidade UAL. Instale para jogar."
                )
                jogos.append({
                    "nome": str(nome),
                    "arquivo": nome_arquivo,
                    "descricao": str(descricao),
                    "download_url": url_download,
                    "tamanho": item.get("size", 0),
                })
            jogos.sort(key=lambda jogo: jogo["nome"].casefold())
            self.fila_background.put(("catalogo", jogos, None))
        except (
            OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError,
            ValueError,
        ) as erro:
            self.fila_background.put(("catalogo", None, str(erro)))

    def _catalogo_carregado(self, jogos, erro):
        self.carregando_loja = False
        if erro:
            for filho in self.loja_conteudo.winfo_children():
                filho.destroy()
            self.loja_status.config(
                text=f"Não foi possível carregar a loja: {erro}"
            )
            RoundedButton(
                self.loja_conteudo, "TENTAR NOVAMENTE",
                self.carregar_catalogo_loja, width=190,
                background=self.c_card, foreground=self.c_accent,
            ).grid(row=0, column=0, padx=10, pady=12, sticky="w")
            return
        self.catalogo_loja = jogos
        self.loja_status.config(
            text=f"{len(jogos)} jogo(s) disponível(is) no catálogo do GitHub."
        )
        self.mostrar_jogos_loja()

    def _jogo_ja_instalado(self, nome_arquivo):
        caminho = os.path.join(self.jogos_dir, nome_arquivo)
        return os.path.isfile(caminho)

    def _imagem_capa_catalogo(self, jogo):
        if "imagem_tk" in jogo:
            return jogo["imagem_tk"]
        largura, altura = 132, 92
        superficie = pygame.Surface((largura, altura))
        cores = ((14, 72, 105), (79, 35, 104), (119, 47, 67), (27, 91, 74))
        cor = cores[sum(ord(letra) for letra in jogo["nome"]) % len(cores)]
        superficie.fill(cor)
        pygame.draw.circle(superficie, (90, 235, 255), (105, 25), 25, 2)
        pygame.draw.circle(superficie, (255, 91, 132), (112, 31), 15, 2)
        pygame.draw.polygon(
            superficie, (12, 21, 38),
            [(0, 92), (37, 55), (64, 76), (91, 45), (132, 80), (132, 92)],
        )
        jogo["imagem_tk"] = tk.PhotoImage(
            master=self.root,
            data=b"P6\n132 92\n255\n" + pygame.image.tostring(superficie, "RGB"),
            format="PPM",
        )
        return jogo["imagem_tk"]

    def mostrar_jogos_loja(self):
        if not hasattr(self, "loja_conteudo"):
            return
        for filho in self.loja_conteudo.winfo_children():
            filho.destroy()
        consulta = self.busca_loja.get().strip().casefold()
        encontrados = [
            jogo for jogo in self.catalogo_loja
            if consulta in jogo["nome"].casefold()
            or consulta in jogo["descricao"].casefold()
        ]
        if not self.catalogo_loja:
            return
        if not encontrados:
            tk.Label(
                self.loja_conteudo,
                text="Nenhum jogo encontrado para essa busca.",
                font=("Segoe UI", 10), bg=self.c_bg, fg=self.c_sub,
            ).grid(row=0, column=0, padx=12, pady=18, sticky="w")
            return
        for indice, jogo in enumerate(encontrados):
            linha, coluna = divmod(indice, 2)
            self._criar_card_loja(jogo, linha, coluna)

    def _criar_card_loja(self, jogo, linha, coluna):
        card = tk.Frame(
            self.loja_conteudo, bg=self.c_card, padx=12, pady=12,
            highlightthickness=1, highlightbackground=self.c_border,
        )
        card.grid(row=linha, column=coluna, sticky="nsew", padx=6, pady=6)
        self.loja_conteudo.grid_columnconfigure(0, weight=1, uniform="loja")
        self.loja_conteudo.grid_columnconfigure(1, weight=1, uniform="loja")
        tk.Label(
            card, image=self._imagem_capa_catalogo(jogo), bg=self.c_card,
        ).pack(side="left", padx=(0, 12), anchor="n")
        detalhes = tk.Frame(card, bg=self.c_card)
        detalhes.pack(side="left", fill="both", expand=True)
        tk.Label(
            detalhes, text=jogo["nome"], font=("Segoe UI", 10, "bold"),
            bg=self.c_card, fg=self.c_text, anchor="w",
            wraplength=230, justify="left",
        ).pack(fill="x", anchor="w")
        tk.Label(
            detalhes, text=jogo["descricao"], font=("Segoe UI", 8),
            bg=self.c_card, fg=self.c_sub, anchor="w",
            wraplength=230, justify="left",
        ).pack(fill="x", anchor="w", pady=(5, 8))
        instalado = self._jogo_ja_instalado(jogo["arquivo"])
        baixando = jogo["arquivo"] in self.downloads_em_andamento
        botao = RoundedButton(
            detalhes,
            "✓   INSTALADO" if instalado else "BAIXANDO..." if baixando else "↓   BAIXAR",
            None if instalado or baixando else lambda item=jogo: self.baixar_jogo_loja(item),
            width=145, height=36,
            background=self.c_green if instalado else self.c_accent,
            foreground="#07150c" if instalado else "#06131b",
            hover_background="#62ffae" if instalado else "#56f4ff",
        )
        botao.pack(anchor="w")
        if instalado or baixando:
            botao.set_enabled(False)

    def baixar_jogo_loja(self, jogo):
        nome_arquivo = jogo["arquivo"]
        if nome_arquivo in self.downloads_em_andamento:
            return
        if self._jogo_ja_instalado(nome_arquivo):
            self.mostrar_jogos_loja()
            return
        self.downloads_em_andamento.add(nome_arquivo)
        self.mostrar_jogos_loja()
        self._ativar_poll_background()
        threading.Thread(
            target=self._baixar_jogo_em_thread, args=(jogo,), daemon=True,
        ).start()

    def _baixar_jogo_em_thread(self, jogo):
        nome_arquivo = jogo["arquivo"]
        caminho_temporario = None
        try:
            requisicao = urllib.request.Request(
                jogo["download_url"],
                headers={"User-Agent": "UAL-Game-Hub"},
            )
            with urllib.request.urlopen(requisicao, timeout=30) as resposta:
                dados = resposta.read(100_000_001)
            if len(dados) > 100_000_000:
                raise ValueError("O jogo excede o limite de download de 100 MB.")
            with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
                membros = pacote.infolist()
                if sum(membro.file_size for membro in membros) > 250_000_000:
                    raise ValueError(
                        "O conteúdo descompactado do jogo excede 250 MB."
                    )
                scripts = [
                    nome for nome in pacote.namelist()
                    if os.path.basename(nome.replace("\\", "/")).casefold()
                    == "main.ualscript"
                ]
                if not scripts:
                    raise ValueError("Este pacote não contém main.ualscript.")
                if len(scripts) > 1:
                    raise ValueError("O pacote contém mais de um main.ualscript.")
                for membro in membros:
                    nome_seguro = membro.filename.replace("\\", "/")
                    partes = nome_seguro.split("/")
                    if (
                        nome_seguro.startswith("/")
                        or any(parte == ".." for parte in partes)
                        or (partes and ":" in partes[0])
                    ):
                        raise ValueError(
                            f"Caminho inválido dentro do jogo: {membro.filename}"
                        )
                membro_corrompido = pacote.testzip()
                if membro_corrompido is not None:
                    raise ValueError(
                        f"O arquivo {membro_corrompido} está corrompido."
                    )

            destino = os.path.join(self.jogos_dir, nome_arquivo)
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".ual_download_", suffix=".tmp",
                dir=self.jogos_dir, delete=False,
            ) as arquivo_temp:
                caminho_temporario = arquivo_temp.name
                arquivo_temp.write(dados)
            if os.path.exists(destino):
                raise FileExistsError("Este jogo já foi instalado.")
            os.replace(caminho_temporario, destino)
            caminho_temporario = None
            self.fila_background.put(("download", nome_arquivo, None))
        except (
            OSError, urllib.error.URLError, zipfile.BadZipFile, RuntimeError,
            ValueError,
        ) as erro:
            self.fila_background.put(("download", nome_arquivo, str(erro)))
        finally:
            if caminho_temporario and os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)

    def _download_concluido(self, nome_arquivo, erro):
        self.downloads_em_andamento.discard(nome_arquivo)
        if erro:
            messagebox.showerror("Falha ao baixar jogo", erro)
        else:
            self.atualizar_biblioteca()
            self.loja_status.config(
                text=f"{os.path.splitext(nome_arquivo)[0]} foi instalado."
            )
        self.mostrar_jogos_loja()

    def construir_aba_mods(self):
        self.aba_mods = tk.Frame(self.main_area, bg=self.c_bg)
        tk.Label(self.aba_mods, text="CONFIGURAÇÕES", font=("Segoe UI", 22, "bold"), bg=self.c_bg, fg=self.c_text).pack(anchor="w", pady=(18, 3))
        tk.Label(
            self.aba_mods, text="Personalize a sua experiência antes de iniciar uma partida.",
            font=("Segoe UI", 10), bg=self.c_bg, fg=self.c_sub,
        ).pack(anchor="w", pady=(0, 16))
        
        self.criar_card_mod(self.aba_mods, "🖥️ Modo Tela Cheia (Fullscreen)", "Inicia o jogo ocupando 100% da sua tela nativa.", self.var_fullscreen)
        self.criar_card_mod(self.aba_mods, "📊 Contador de FPS (HUD)", "Exibe a taxa de quadros em tempo real.", self.var_show_fps)
        self.criar_card_mod(self.aba_mods, "⌨️ Keystrokes Mod", "Mostra as teclas W, A, S, D na tela acendendo em Ciano.", self.var_keystrokes)
        self.criar_card_mod(self.aba_mods, "🟩 Hitbox Viewer (Modo Debug)", "Desenha bordas neon ao redor da colisão dos objetos.", self.var_debug)
        
        card_fps = tk.Frame(
            self.aba_mods, bg=self.c_card, padx=20, pady=15,
            highlightthickness=1, highlightbackground=self.c_border,
        )
        card_fps.pack(fill="x", padx=40, pady=8)
        tk.Label(card_fps, text="🚀 Limite de FPS Boost:", font=("Segoe UI", 12, "bold"), bg=self.c_card, fg="white").pack(side="left")
        
        combo = ttk.Combobox(card_fps, textvariable=self.var_fps, values=["60 FPS", "120 FPS", "144 FPS", "240 FPS", "Ilimitado (Max Boost)"], state="readonly", font=("Segoe UI", 10), width=22)
        combo.pack(side="right")
        tk.Label(
            self.aba_mods,
            text="Dica: durante o jogo, F alterna a tela cheia e ESC sai dela.",
            font=("Segoe UI", 9), bg=self.c_bg, fg=self.c_sub,
        ).pack(anchor="w", padx=40, pady=(8, 0))

    def criar_card_mod(self, parent, titulo, desc, variavel):
        card = tk.Frame(
            parent, bg=self.c_card, padx=20, pady=15,
            highlightthickness=1, highlightbackground=self.c_border,
        )
        card.pack(fill="x", padx=40, pady=8)
        
        f_txt = tk.Frame(card, bg=self.c_card)
        f_txt.pack(side="left")
        tk.Label(f_txt, text=titulo, font=("Segoe UI", 12, "bold"), bg=self.c_card, fg=self.c_text).pack(anchor="w")
        tk.Label(f_txt, text=desc, font=("Segoe UI", 9), bg=self.c_card, fg=self.c_sub).pack(anchor="w", pady=(2, 0))
        
        chk = tk.Checkbutton(card, text="ATIVO", variable=variavel, bg=self.c_card, fg=self.c_accent, selectcolor=self.c_bg,
                             activebackground=self.c_card, activeforeground=self.c_accent, font=("Segoe UI", 10, "bold"), cursor="hand2")
        chk.pack(side="right")

    def iniciar(self):
        self.root.mainloop()

if __name__ == "__main__":
    LunarLauncherUAL().iniciar()
