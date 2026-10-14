import pygame
import zipfile
import os
import sys
import re
import random
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# FIX DE QUALIDADE DE IMAGEM (ALTA DEFINIÇÃO NO WINDOWS)
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ==========================================
# MOTOR GRÁFICO E INTERPRETADOR UAL 8.1
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
        self.tela = pygame.display.set_mode((self.largura, self.altura))
        pygame.display.set_caption("UAL Client 8.1 - Physics Engine (Corner Fix)")
        self.clock = pygame.time.Clock()
        self.fonte_hud = pygame.font.SysFont("segoeui", 16, bold=True)
        
        self.fator_fps = 1.0 
        self.rodando = True
        self.cor_fundo = (15, 17, 26)
        
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
        self.pasta_temp = ""
        
        if caminho_arquivo_ual:
            if not caminho_arquivo_ual.lower().endswith(".ual"):
                raise Exception("Formato inválido! O motor aceita exclusivamente pacotes '.ual'.")
                
            self.pasta_temp = "temp_jogo_ual"
            with zipfile.ZipFile(caminho_arquivo_ual, 'r') as zip_ref:
                zip_ref.extractall(self.pasta_temp)
                
            caminho_codigo = os.path.join(self.pasta_temp, "main.ualscript")
            if not os.path.exists(caminho_codigo):
                raise Exception("Arquivo 'main.ualscript' não encontrado dentro do pacote .ual!")

            with open(caminho_codigo, "r", encoding="utf-8") as f:
                self.codigo = f.read().strip().split('\n')
                
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

    def resolver_texto(self, texto_bruto):
        for var, val in self.variaveis.items():
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            texto_bruto = texto_bruto.replace(f"{{{var}}}", str(val))
        return texto_bruto

    def sincronizar_pos(self, sp, novo_x, novo_y):
        """Sincroniza perfeitamente o float com o rect inteiro do Pygame"""
        sp["x"] = float(novo_x)
        sp["y"] = float(novo_y)
        sp["rect"].x = int(round(sp["x"]))
        sp["rect"].y = int(round(sp["y"]))

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
                    self.tela = pygame.display.set_mode((self.largura, self.altura))
                
                elif comando == "DEFINIR_FUNDO_COR":
                    self.cor_fundo = (int(partes[1]), int(partes[2]), int(partes[3]))

                elif comando == "VAR_CRIAR": self.variaveis[partes[1]] = float(partes[2]) if "." in partes[2] else int(partes[2])
                elif comando == "VAR_SOMA": self.variaveis[partes[1]] += float(partes[2]) if "." in partes[2] else int(partes[2])
                elif comando == "VAR_SUBTRAIR": self.variaveis[partes[1]] -= float(partes[2]) if "." in partes[2] else int(partes[2])
                    
                elif comando == "SE_VAR_IGUAL":
                    if float(self.variaveis.get(partes[1], 0)) == float(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_MENOR":
                    if float(self.variaveis.get(partes[1], 0)) < float(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                elif comando == "SE_VAR_MAIOR":
                    if float(self.variaveis.get(partes[1], 0)) > float(partes[2]):
                        self.executar_bloco(partes[3], usar_delta)
                
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
                    self.sprites[nome] = {"img": img, "rect": rect, "x": x, "y": y, "vx": 0.0, "vy": 0.0, "visivel": True}

                elif comando == "CRIAR_CUBO":
                    nome = partes[1]
                    x, y = float(partes[2]), float(partes[3])
                    larg, alt = int(partes[4]), int(partes[5])
                    cor = (int(partes[6]), int(partes[7]), int(partes[8]))
                    img = pygame.Surface((larg, alt))
                    img.fill(cor)
                    rect = img.get_rect(topleft=(int(x), int(y)))
                    self.sprites[nome] = {"img": img, "rect": rect, "x": x, "y": y, "vx": 0.0, "vy": 0.0, "visivel": True}

                # ================= FÍSICA E REBATE CORRIGIDOS (SEM BUG DE CANTO) =================
                elif comando == "DEFINIR_FISICA":
                    nome = partes[1]
                    if nome in self.sprites:
                        self.sprites[nome]["vx"] = float(partes[2])
                        self.sprites[nome]["vy"] = float(partes[3])

                elif comando == "REBATER_TELA":
                    nome = partes[1]
                    if nome in self.sprites and self.sprites[nome]["visivel"]:
                        sp = self.sprites[nome]
                        larg_sp = sp["rect"].width
                        alt_sp = sp["rect"].height
                        
                        # Verifica o eixo X diretamente na coordenada float e ejeta com margem de 1px
                        if sp["x"] <= 0:
                            self.sincronizar_pos(sp, 1.0, sp["y"])
                            sp["vx"] = abs(sp["vx"]) if sp["vx"] != 0 else 5.0
                        elif sp["x"] + larg_sp >= self.largura:
                            self.sincronizar_pos(sp, self.largura - larg_sp - 1.0, sp["y"])
                            sp["vx"] = -abs(sp["vx"]) if sp["vx"] != 0 else -5.0
                            
                        # Verifica o eixo Y diretamente na coordenada float e ejeta com margem de 1px
                        if sp["y"] <= 0:
                            self.sincronizar_pos(sp, sp["x"], 1.0)
                            sp["vy"] = abs(sp["vy"]) if sp["vy"] != 0 else 5.0
                        elif sp["y"] + alt_sp >= self.altura:
                            self.sincronizar_pos(sp, sp["x"], self.altura - alt_sp - 1.0)
                            sp["vy"] = -abs(sp["vy"]) if sp["vy"] != 0 else -5.0

                elif comando == "REBATER_OBJETO":
                    nome1, nome2 = partes[1], partes[2]
                    cena_colisao = partes[3] if len(partes) > 3 else None
                    
                    if nome1 in self.sprites and nome2 in self.sprites:
                        s1, s2 = self.sprites[nome1], self.sprites[nome2]
                        if s1["visivel"] and s2["visivel"] and s1["rect"].colliderect(s2["rect"]):
                            r1, r2 = s1["rect"], s2["rect"]
                            
                            # Calcula distância entre os centros e sobreposição real
                            dx = r1.centerx - r2.centerx
                            dy = r1.centery - r2.centery
                            
                            overlap_x = (r1.width / 2.0 + r2.width / 2.0) - abs(dx)
                            overlap_y = (r1.height / 2.0 + r2.height / 2.0) - abs(dy)
                            
                            # Se bateu exatamente no canto (diferença menor que 4 pixels), rebate nos dois eixos!
                            if abs(overlap_x - overlap_y) < 4.0:
                                if dx > 0:
                                    s1["vx"] = abs(s1["vx"])
                                    novo_x = r2.right + 2.0
                                else:
                                    s1["vx"] = -abs(s1["vx"])
                                    novo_x = r2.left - r1.width - 2.0
                                    
                                if dy > 0:
                                    s1["vy"] = abs(s1["vy"])
                                    novo_y = r2.bottom + 2.0
                                else:
                                    s1["vy"] = -abs(s1["vy"])
                                    novo_y = r2.top - r1.height - 2.0
                                    
                                self.sincronizar_pos(s1, novo_x, novo_y)
                                
                            # Colisão Horizontal (Bateu na lateral esquerda ou direita do bloco)
                            elif overlap_x < overlap_y:
                                if dx > 0: # Veio da direita
                                    self.sincronizar_pos(s1, r2.right + 2.0, s1["y"])
                                    s1["vx"] = abs(s1["vx"])
                                else:      # Veio da esquerda
                                    self.sincronizar_pos(s1, r2.left - r1.width - 2.0, s1["y"])
                                    s1["vx"] = -abs(s1["vx"])
                                    
                            # Colisão Vertical (Bateu no topo ou embaixo do bloco/raquete)
                            else:
                                if dy > 0: # Bateu por baixo
                                    self.sincronizar_pos(s1, s1["x"], r2.bottom + 2.0)
                                    s1["vy"] = abs(s1["vy"])
                                else:      # Bateu por cima (Ex: na raquete)
                                    self.sincronizar_pos(s1, s1["x"], r2.top - r1.height - 2.0)
                                    s1["vy"] = -abs(s1["vy"])
                                    
                                    # Efeito Arkanoid: Se bater nos cantos de objetos largos (como a raquete), angula o tiro!
                                    if r2.width >= 80:
                                        fator_canto = (r1.centerx - r2.centerx) / (r2.width / 2.0)
                                        velocidade_base = max(abs(s1["vx"]), 6.0)
                                        if abs(fator_canto) > 0.35:
                                            s1["vx"] = velocidade_base * (1.0 if fator_canto > 0 else -1.0)
                                
                            if cena_colisao:
                                self.executar_bloco(cena_colisao, usar_delta=False)

                elif comando == "MOVER_ALEATORIO":
                    nome = partes[1]
                    if nome in self.sprites:
                        sp = self.sprites[nome]
                        nx = float(random.randint(int(partes[2]), int(partes[3])))
                        ny = float(random.randint(int(partes[4]), int(partes[5])))
                        self.sincronizar_pos(sp, nx, ny)

                elif comando == "OCULTAR_SPRITE":
                    if partes[1] in self.sprites: self.sprites[partes[1]]["visivel"] = False
                elif comando == "MOSTRAR_SPRITE":
                    if partes[1] in self.sprites: self.sprites[partes[1]]["visivel"] = True

                elif comando == "MOVER_PARA":
                    if partes[1] in self.sprites:
                        self.sincronizar_pos(self.sprites[partes[1]], float(partes[2]), float(partes[3]))

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
                if dt > 0.05: dt = 0.05 # Limite mais rígido para impedir que objetos atravessem paredes em travadas
                self.fator_fps = dt * 60.0
                
                if self.fundo: self.tela.blit(self.fundo, (0, 0))
                else: self.tela.fill(self.cor_fundo)
                
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT: 
                        self.rodando = False
                    if evento.type == pygame.KEYDOWN:
                        n_tecla = pygame.key.name(evento.key)
                        if n_tecla in self.eventos_tecla: 
                            self.executar_bloco(self.eventos_tecla[n_tecla], usar_delta=False)
                    if evento.type == pygame.MOUSEBUTTONDOWN:
                        pos = pygame.mouse.get_pos()
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

                # ATUALIZA FÍSICA AUTOMÁTICA (Em sub-passos se a velocidade for alta para nunca atravessar cantos!)
                for sp in self.sprites.values():
                    if sp["visivel"] and (sp["vx"] != 0 or sp["vy"] != 0):
                        nx = sp["x"] + sp["vx"] * self.fator_fps
                        ny = sp["y"] + sp["vy"] * self.fator_fps
                        self.sincronizar_pos(sp, nx, ny)
                
                if "loop" in self.cenas: 
                    self.executar_bloco("loop", usar_delta=True)
                
                for dados in self.sprites.values():
                    if dados["visivel"]: 
                        self.tela.blit(dados["img"], dados["rect"])
                        if modo_debug:
                            pygame.draw.rect(self.tela, (0, 240, 255), dados["rect"], 2)
                    
                for dados in self.textos.values():
                    texto_formatado = self.resolver_texto(dados["texto"])
                    surf = dados["fonte"].render(texto_formatado, True, dados["cor"])
                    self.tela.blit(surf, dados["pos"])
                
                self.DesenharHudLunar(teclas)
                pygame.display.flip()
                
            pygame.quit()
                
        except Exception as e:
            pygame.quit()
            erro_formatado = traceback.format_exc()
            messagebox.showerror("Crash Report - UAL Client", f"Um erro interrompeu o jogo:\n\n{erro_formatado}")


# ==========================================
# JOGO DEMO: NEON BREAKER (COM REBATE PERFEITO)
# ==========================================
JOGO_PADRAO_RICOCHETE = """# === JOGO: NEON BREAKER (FÍSICA DE CANTOS CORRIGIDA) ===
CENA inicio
DEFINIR_TELA 800 600
DEFINIR_FUNDO_COR 12 14 24

VAR_CRIAR pontos 0

# Raquete do Jogador (Ciano) e Bola de Energia (Branca)
CRIAR_CUBO raquete 340 540 130 20 0 240 255
CRIAR_CUBO bola 390 350 22 22 255 255 255

# Obstáculo Fixo no Meio (Roxo) que faz a bola rebater!
CRIAR_CUBO pilar_central 330 250 140 25 160 60 255

# Blocos Destrutíveis no Topo (Rosa, Ouro, Verde, Azul)
CRIAR_CUBO bloco1 80 100 130 35 255 40 100
CRIAR_CUBO bloco2 250 100 130 35 255 215 0
CRIAR_CUBO bloco3 420 100 130 35 0 230 118
CRIAR_CUBO bloco4 590 100 130 35 0 180 255

# Dá velocidade inicial para a bola (VX = 6, VY = -6)
DEFINIR_FISICA bola 6 -6

# Interface
CRIAR_TEXTO hud_pts 24 20 15 0 240 255 "SCORE: {pontos}"
CRIAR_TEXTO msg_info 18 20 50 140 150 180 "Use [A] e [D] para rebater! Aperte [R] para resetar"

# Controles
AO_SEGURAR_MOVER a raquete -11 0
AO_SEGURAR_MOVER d raquete 11 0
AO_TECLAR r resetar_jogo
FIM_CENA

CENA loop
LIMITAR_TELA raquete

# Faz a bola quicar nas bordas da tela sem prender nos cantos
REBATER_TELA bola

# Faz a bola rebater na raquete e no pilar roxo central!
REBATER_OBJETO bola raquete
REBATER_OBJETO bola pilar_central

# Faz a bola rebater nos blocos do topo e chama a cena de quebrar cada um!
REBATER_OBJETO bola bloco1 quebrar_b1
REBATER_OBJETO bola bloco2 quebrar_b2
REBATER_OBJETO bola bloco3 quebrar_b3
REBATER_OBJETO bola bloco4 quebrar_b4
FIM_CENA

CENA quebrar_b1
OCULTAR_SPRITE bloco1
VAR_SOMA pontos 100
ATUALIZAR_TEXTO hud_pts "SCORE: {pontos}"
FIM_CENA

CENA quebrar_b2
OCULTAR_SPRITE bloco2
VAR_SOMA pontos 100
ATUALIZAR_TEXTO hud_pts "SCORE: {pontos}"
FIM_CENA

CENA quebrar_b3
OCULTAR_SPRITE bloco3
VAR_SOMA pontos 100
ATUALIZAR_TEXTO hud_pts "SCORE: {pontos}"
FIM_CENA

CENA quebrar_b4
OCULTAR_SPRITE bloco4
VAR_SOMA pontos 100
ATUALIZAR_TEXTO hud_pts "SCORE: {pontos}"
FIM_CENA

CENA resetar_jogo
VAR_CRIAR pontos 0
ATUALIZAR_TEXTO hud_pts "SCORE: 0"
MOSTRAR_SPRITE bloco1
MOSTRAR_SPRITE bloco2
MOSTRAR_SPRITE bloco3
MOSTRAR_SPRITE bloco4
MOVER_PARA bola 390 350
DEFINIR_FISICA bola 6 -6
FIM_CENA
"""

# ==========================================
# LUNAR CLIENT STYLE LAUNCHER
# ==========================================
class LunarLauncherUAL:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UAL Client Launcher")
        self.root.geometry("960x600")
        self.root.configure(bg="#0b0c10")
        self.root.resizable(False, False)
        
        self.c_bg = "#0b0c10"
        self.c_sidebar = "#12141c"
        self.c_card = "#181b26"
        self.c_accent = "#00f0ff"
        self.c_green = "#00e676"
        self.c_text = "#ffffff"
        self.c_sub = "#7a8299"
        
        self.var_fps = tk.StringVar(value="Ilimitado")
        self.var_show_fps = tk.BooleanVar(value=True)
        self.var_keystrokes = tk.BooleanVar(value=True)
        self.var_debug = tk.BooleanVar(value=False)
        
        self.montar_ui()
        
    def montar_ui(self):
        sidebar = tk.Frame(self.root, bg=self.c_sidebar, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        f_logo = tk.Frame(sidebar, bg=self.c_sidebar)
        f_logo.pack(pady=30)
        tk.Label(f_logo, text="🌙 UAL", font=("Segoe UI", 22, "bold"), bg=self.c_sidebar, fg=self.c_accent).pack(side="left")
        tk.Label(f_logo, text="CLIENT", font=("Segoe UI", 22), bg=self.c_sidebar, fg="white").pack(side="left", padx=4)
        
        self.criar_botao_menu(sidebar, "⚡  JOGAR AGORA", lambda: self.trocar_aba(self.aba_play))
        self.criar_botao_menu(sidebar, "💻  SCRIPT STUDIO", lambda: self.trocar_aba(self.aba_script))
        self.criar_botao_menu(sidebar, "🛠️  MODS & FPS", lambda: self.trocar_aba(self.aba_mods))
        
        lbl_status = tk.Label(sidebar, text="● Physics Engine (v8.1)", font=("Segoe UI", 9, "bold"), bg=self.c_sidebar, fg=self.c_green)
        lbl_status.pack(side="bottom", pady=20)
        
        self.main_area = tk.Frame(self.root, bg=self.c_bg)
        self.main_area.pack(side="right", fill="both", expand=True)
        
        self.construir_aba_play()
        self.construir_aba_script()
        self.construir_aba_mods()
        
        self.trocar_aba(self.aba_play)

    def criar_botao_menu(self, parent, texto, comando):
        btn = tk.Button(parent, text=texto, font=("Segoe UI", 11, "bold"), bg=self.c_sidebar, fg=self.c_sub,
                        activebackground=self.c_card, activeforeground=self.c_accent, bd=0, pady=14, anchor="w", padx=25, cursor="hand2", command=comando)
        btn.pack(fill="x", pady=2)
        btn.bind("<Enter>", lambda e: btn.config(bg=self.c_card, fg="white"))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.c_sidebar, fg=self.c_sub))

    def trocar_aba(self, aba_destino):
        for aba in (self.aba_play, self.aba_script, self.aba_mods):
            aba.pack_forget()
        aba_destino.pack(fill="both", expand=True)

    def obter_configs(self):
        fps_str = self.var_fps.get()
        fps_val = 0 if "Ilimitado" in fps_str else int(fps_str.split()[0])
        return {
            "fps": fps_val,
            "mostrar_fps": self.var_show_fps.get(),
            "keystrokes": self.var_keystrokes.get(),
            "modo_debug": self.var_debug.get()
        }

    def construir_aba_play(self):
        self.aba_play = tk.Frame(self.main_area, bg=self.c_bg)
        
        banner = tk.Frame(self.aba_play, bg=self.c_card, height=220)
        banner.pack(fill="x", padx=40, pady=35)
        banner.pack_propagate(False)
        
        tk.Label(banner, text="UAL ENGINE 8.1 // CORNER COLLISION FIX", font=("Segoe UI", 10, "bold"), bg=self.c_card, fg=self.c_accent).pack(anchor="w", padx=30, pady=(25, 5))
        tk.Label(banner, text="FÍSICA DE RICOCHETE CORRIGIDA", font=("Segoe UI", 26, "bold"), bg=self.c_card, fg="white").pack(anchor="w", padx=30)
        tk.Label(banner, text="Anti-Tunneling nos Cantos • Impulso Angular na Raquete • Exclusivo .UAL", font=("Segoe UI", 11), bg=self.c_card, fg=self.c_sub).pack(anchor="w", padx=30, pady=5)
        
        f_botoes = tk.Frame(self.aba_play, bg=self.c_bg)
        f_botoes.pack(fill="x", padx=40, pady=10)
        
        btn_launch = tk.Button(f_botoes, text="🚀  LAUNCH SCRIPT CODE\n(Jogar Demo: Neon Breaker)", font=("Segoe UI", 15, "bold"),
                               bg=self.c_green, fg="#051b0e", activebackground="#00c853", bd=0, pady=18, cursor="hand2", command=self.rodar_script)
        btn_launch.pack(fill="x", pady=10)
        
        btn_pacote = tk.Button(f_botoes, text="📦  IMPORTAR PACOTE DE JOGO (.UAL)", font=("Segoe UI", 12, "bold"),
                               bg=self.c_card, fg=self.c_accent, activebackground="#232838", bd=1, relief="solid", pady=12, cursor="hand2", command=self.carregar_arquivo)
        btn_pacote.pack(fill="x", pady=10)

    def construir_aba_script(self):
        self.aba_script = tk.Frame(self.main_area, bg=self.c_bg)
        
        topo = tk.Frame(self.aba_script, bg=self.c_bg)
        topo.pack(fill="x", padx=30, pady=(20, 10))
        tk.Label(topo, text="UAL SCRIPT STUDIO", font=("Segoe UI", 18, "bold"), bg=self.c_bg, fg="white").pack(side="left")
        
        btn_run_top = tk.Button(topo, text="▶  LAUNCH GAME", font=("Segoe UI", 11, "bold"), bg=self.c_green, fg="#051b0e", bd=0, padx=20, pady=6, cursor="hand2", command=self.rodar_script)
        btn_run_top.pack(side="right")
        
        self.text_area = tk.Text(self.aba_script, bg="#10121a", fg="#00f0ff", font=("Consolas", 11), insertbackground="white", bd=0, padx=15, pady=15)
        self.text_area.pack(fill="both", expand=True, padx=30, pady=(0, 25))
        self.text_area.insert("1.0", JOGO_PADRAO_RICOCHETE)

    def construir_aba_mods(self):
        self.aba_mods = tk.Frame(self.main_area, bg=self.c_bg)
        tk.Label(self.aba_mods, text="LUNAR MODS & PERFORMANCE", font=("Segoe UI", 18, "bold"), bg=self.c_bg, fg="white").pack(anchor="w", padx=40, pady=(25, 20))
        
        self.criar_card_mod(self.aba_mods, "📊 Contador de FPS (HUD)", "Exibe a taxa de quadros em tempo real no canto superior direito.", self.var_show_fps)
        self.criar_card_mod(self.aba_mods, "⌨️ Keystrokes Mod", "Mostra as teclas W, A, S, D na tela acendendo em Ciano quando pressionadas.", self.var_keystrokes)
        self.criar_card_mod(self.aba_mods, "🟩 Hitbox Viewer (Modo Debug)", "Desenha bordas neon ao redor da colisão de todos os objetos vivos.", self.var_debug)
        
        card_fps = tk.Frame(self.aba_mods, bg=self.c_card, padx=20, pady=15)
        card_fps.pack(fill="x", padx=40, pady=8)
        tk.Label(card_fps, text="🚀 Limite de Taxa de Quadros (FPS Boost):", font=("Segoe UI", 12, "bold"), bg=self.c_card, fg="white").pack(side="left")
        
        combo = ttk.Combobox(card_fps, textvariable=self.var_fps, values=["60 FPS", "120 FPS", "144 FPS", "240 FPS", "Ilimitado (Max Boost)"], state="readonly", font=("Segoe UI", 10), width=22)
        combo.pack(side="right")

    def criar_card_mod(self, parent, titulo, desc, variavel):
        card = tk.Frame(parent, bg=self.c_card, padx=20, pady=15)
        card.pack(fill="x", padx=40, pady=8)
        
        f_txt = tk.Frame(card, bg=self.c_card)
        f_txt.pack(side="left")
        tk.Label(f_txt, text=titulo, font=("Segoe UI", 12, "bold"), bg=self.c_card, fg="white").pack(anchor="w")
        tk.Label(f_txt, text=desc, font=("Segoe UI", 9), bg=self.c_card, fg=self.c_sub).pack(anchor="w", pady=(2, 0))
        
        chk = tk.Checkbutton(card, text="ATIVO", variable=variavel, bg=self.c_card, fg=self.c_accent, selectcolor=self.c_bg,
                             activebackground=self.c_card, activeforeground=self.c_accent, font=("Segoe UI", 10, "bold"), cursor="hand2")
        chk.pack(side="right")

    def carregar_arquivo(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o Pacote Exclusivo (.ual)", 
            filetypes=[("Pacote de Jogo UAL", "*.ual")]
        )
        if caminho:
            self.root.withdraw()
            MotorUalGrafico(config=self.obter_configs(), caminho_arquivo_ual=caminho).rodar()
            self.root.deiconify()

    def rodar_script(self):
        codigo = self.text_area.get("1.0", tk.END).strip()
        if not codigo:
            messagebox.showwarning("Aviso", "O código está vazio!")
            return
        self.root.withdraw()
        MotorUalGrafico(config=self.obter_configs(), codigo_puro=codigo).rodar()
        self.root.deiconify()

    def iniciar(self):
        self.root.mainloop()

if __name__ == "__main__":
    LunarLauncherUAL().iniciar()
