import pygame
import random
import sys
from dataclasses import dataclass, field

class Moveable:
    def __init__(self, x, y):
        self.speed = 25
        self.moving = False
        self.pos = pygame.math.Vector2(x, y)
        self.direction = pygame.math.Vector2(0, 0)
        self.target = pygame.Vector2(x, y)
        self.action_on_stop_moving = None
        self.has_moved = False

    def move_to(self, x, y, speed = None):
        self.has_moved = False
        if speed != None:
            self.speed = speed
        self.moving = True
        self.target = pygame.math.Vector2(x, y)
        self.direction = self.pos - self.target
        if self.direction.length() > 0:
            self.direction = self.direction.normalize()
        else:
            self.direction = pygame.math.Vector2(0, 0)

    def update(self):
        if self.moving:
            if self.pos.distance_to(self.target) < self.speed:
                self.pos = self.target
                self.moving = False
                if self.action_on_stop_moving != None and self.has_moved:
                    self.action_on_stop_moving()
            else:
                self.has_moved = True
                self.pos -= self.direction * self.speed

class Chip(Moveable):
    def __init__(self, x, y, image: pygame.Surface):
        super().__init__(x, y)
        self.in_bet = False
        self.chip_rect = image.get_rect(center=(x, y))
        self.image = image

    def draw(self, game_surface):
        game_surface.blit(self.image, self.chip_rect)

    def update(self):
        super().update()
        self.chip_rect.center = (int(self.pos.x), int(self.pos.y))

    def move_offscreen(self):
        self.move_to(-25,-25)

    def reset_pos(self):
        self.move_to(self.default_pos.x, self.default_pos.y)

class Card(Moveable):
    def __init__(self, x, y, suit: str, rank: str, front: pygame.Surface, back: pygame.Surface, face_up: bool = False):
        super().__init__(x, y)
        self.suit = suit
        self.rank = rank
        self.front = front
        self.back = back
        self.face_up = face_up
        self.flipping = False
        self.flip_target = not self.face_up
        self.flip_speed = 25
        self.flip_direction = -1 # -1 for shrinking, 1 for growing. 
        self.original_width = self.front.get_width()
        self.current_width = self.original_width
        self.original_height = self.front.get_height()
        self.current_height = self.original_height

    def __str__(self):
        return f"{self.rank} of {self.suit}"

    def flip(self):
        self.flip_direction = -1
        self.flipping = True
        self.flip_target = not self.face_up

    def draw(self, game_surface):
        if self.flipping:
            flip_image = self.front if self.face_up else self.back
            flip_image = pygame.transform.scale(flip_image, (int(self.current_width), self.current_height))
            draw_rect = flip_image.get_rect()
            center_x = self.pos.x + (self.original_width // 2)
            center_y = self.pos.y + (self.original_height // 2)
            draw_rect.center = (center_x, center_y)
            game_surface.blit(flip_image, draw_rect)
        else:
            game_surface.blit(self.front if self.face_up else self.back, (self.pos.x, self.pos.y))

    def update(self):
        super().update()

        #Card 3D flip effect
        if self.flipping:
            self.current_width += self.flip_speed * self.flip_direction 
            if self.face_up == self.flip_target:
                if self.current_width > self.original_width:
                    self.flipping = False
                    self.current_width = self.original_width
            else:
                if self.current_width < 0:
                    self.face_up = self.flip_target
                    self.flip_direction = 1
                    self.current_width = 1

class Deck:
    def __init__(self, images, x, y, cards: list[Card] | None = None, num_decks = 2):
        self.images = images
        self.x = x
        self.y = y
        if cards:
            self.starting_cards = cards
            self.cards = cards
        else:
            ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
            suits = ["spades", "diamonds", "hearts", "clubs"]
            self.starting_cards = [Card(0, 0, suit, rank, images[f"{suit}_{rank}"], images["card_back"]) for i in range(num_decks) for suit in suits for rank in ranks]
            self.cards = self.starting_cards.copy()
            self.shuffle_deck()

    def __len__(self):
        return len(self.cards)
    
    def shuffle_deck(self):
        random.shuffle(self.cards)

    def deal_card(self) -> Card:
        if len(self) == 0:
            self.cards = self.starting_cards.copy()

            for card in self.cards:#reset card faces when reshuffling. 
                card.face_up = False
                card.flipping = False
                card.current_width = card.original_width

            self.shuffle_deck()
        return self.cards.pop()
    
    def draw(self, game_surface):
        for i in range(len(self.cards)):
            game_surface.blit(self.images["card_back"], (self.x+int(i*0.25), self.y-int(i*0.25)))

class Hand:
    def __init__(self, cards: list[Card], x = 0, y = 0, card_stack_spacing = 23):
        self.cards = cards
        self.aces = self.get_aces_count()
        self.value = self.get_value()
        self.card_stack_spacing_x = card_stack_spacing
        self.x = x
        self.y = y

    def __len__(self) -> int:
        return len(self.cards)

    def get_aces_count(self):
        aces = 0
        for card in self.cards:
            if card.rank == "A":
                aces += 1
        return aces

    def get_value(self):
        value = 0
        aces = self.get_aces_count()
        faces = "JQK"
        for card in self.cards:
            if card.rank in faces:
                value += 10
            elif card.rank == "A":
                value += 11
            else:
                value += int(card.rank)
        while aces > 0 and value > 21:
            aces -= 1
            value -= 10
        return value
    
@dataclass
class Text:
    x: int
    y: int
    text: str
    font_size: int = 30
    font: pygame.font.Font = field(init = False)
    text_offset_x: int = 0
    text_offset_y: int = 0
    color: tuple = (0, 0, 0)
    scale_factor: float = 1.0

    def __post_init__(self):
        self.font = pygame.font.Font(None, self.font_size)
        self.text_surface = self.font.render(self.text, True, self.color)
        self.scaled_text_surface = pygame.transform.scale_by(self.text_surface, self.scale_factor)

    def set_text(self, text):
        previous_width = self.text_surface.get_width()
        self.text = text
        self.text_surface = self.font.render(self.text, True, self.color)
        new_width = self.text_surface.get_width()
        self.text_offset_x -= int((new_width - previous_width)/2) #keep text centered even when adding characters. 
        self.scaled_text_surface = pygame.transform.scale_by(self.text_surface, self.scale_factor)

    def scale_by(self, scale_factor):
        self.scale_factor *= scale_factor
        self.scaled_text_surface = pygame.transform.scale_by(self.text_surface, self.scale_factor)

    def draw(self, game_surface):
        game_surface.blit(self.scaled_text_surface, (self.x + self.text_offset_x, self.y + self.text_offset_y))


@dataclass 
class Button:
    x: int
    y: int
    width: int
    height: int
    text: str
    text_color: tuple = (0, 0, 0)
    font_size: int = 25
    color: tuple = (255, 255, 255)
    border_color: tuple = (0, 0, 0)
    border_width: int = 3
    border_radius: int = 10
    hover_color: tuple = (235, 235, 235)
    clicked_color: tuple = (155, 155, 155)
    rect: pygame.Rect = field(init = False)
    font: pygame.font.Font = field(init = False)
    font_offset_y: int = 0
    font_offset_x: int = 0
    travel_distance: int = 10
    speed: int = 1
    action: object = None
    frame: int = 0
    clickable: bool = False
    alpha: int = 0

    def __post_init__(self):
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.rect.center = (self.x, self.y)
        self.font = pygame.font.Font(None, self.font_size)
        self.default_color = self.color
        self.text_surface = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        self.clicked = False

    def draw(self, game_surface):
        if self.clickable:
            current_color = self.color
            current_border_color = self.border_color
        else:
            current_color = (150, 150, 150)        
            current_border_color = (100, 100, 100)
            self.frame = self.travel_distance//2
        
        pygame.draw.rect(game_surface, current_color, self.rect.move(0, self.travel_distance), border_radius = self.border_radius) #button bottom
        pygame.draw.rect(game_surface, current_border_color, self.rect.move(0, self.travel_distance), width = self.border_width, border_radius = self.border_radius)#button bottom Border
        pygame.draw.rect(game_surface, current_color, self.rect.move(0, self.frame), border_radius = self.border_radius) #button top
        pygame.draw.rect(game_surface, current_border_color, self.rect.move(0, self.frame), width = self.border_width, border_radius = self.border_radius)#button Border
        if self.clickable:
            self.text_surface.set_alpha(255)
        else:
            self.text_surface.set_alpha(128)
        game_surface.blit(self.text_surface, self.text_rect.move(self.font_offset_x, self.frame + self.font_offset_y))

    def update(self, mouse_pos):
        if self.clickable:
            if self.frame > 0:
                self.frame -= self.speed
            if not self.clicked:
                if self.rect.collidepoint(mouse_pos):
                    self.color = self.hover_color
                else:
                    self.color = self.default_color
class AssetManager:
    def __init__(self):
        pygame.mixer.init()
        self.sounds = {}
        self.card_images = {}
        self.poker_chip_images = []

        self.load_card_images(150, 210)
        self.load_chip_images(50, 50, range(0, 360, 10))
        self.load_audio()

    def load_chip_images(self, width, height, angles):
        #Generate chip images rotated different angles. 
        THICKNESS = 4
        for angle in angles:
            unscaled_image = pygame.image.load("images/Poker Chip.png").convert_alpha()
            scaled_image = pygame.transform.smoothscale(unscaled_image, (width, height))

            scaled_image = pygame.transform.rotate(scaled_image, angle)
            final_chip = pygame.Surface((scaled_image.get_width(), scaled_image.get_height() + THICKNESS), pygame.SRCALPHA)

            bottom_layer = scaled_image.copy() 
            bottom_layer.fill((150, 150, 150), special_flags=pygame.BLEND_RGB_MULT)

            #stack chip image multiple times 
            for i in range(THICKNESS):
                final_chip.blit(bottom_layer, (0, THICKNESS - i))
            final_chip.blit(scaled_image, (0, 0))

            self.poker_chip_images.append(final_chip)

    def load_card_images(self, width, height):
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        suits = ["spades", "diamonds", "hearts", "clubs"]

        THICKNESS = 2
        BORDER_RADIUS = 3
        EDGE_COLOR = (110, 110, 110)

        for rank in ranks:
            for suit in suits:
                key = f"{suit}_{rank}"
                path = f"images/{suit}_{rank}.jpg"

                unscaled_image = pygame.image.load(path).convert_alpha()
                scaled_card_image = pygame.transform.smoothscale(unscaled_image, (width, height))

                #Round corners of card
                rect = scaled_card_image.get_rect()
                mask = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255), rect, border_radius = BORDER_RADIUS)
                scaled_card_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

                #Stamp each card onto a layer to give 3d effect. 
                final_image = pygame.Surface((width, height + THICKNESS), pygame.SRCALPHA)
                edge_rect = pygame.Rect(0, THICKNESS, width, height)
                pygame.draw.rect(final_image, EDGE_COLOR, edge_rect, border_radius = BORDER_RADIUS)
                final_image.blit(scaled_card_image, (0, 0))

                self.card_images[key] = final_image



        unscaled_card_back = pygame.image.load("images/back.jpg").convert_alpha()
        scaled_card_back = pygame.transform.smoothscale(unscaled_card_back, (width, height))

        rect = scaled_card_back.get_rect()
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255), rect, border_radius = BORDER_RADIUS)
        scaled_card_back.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        final_image = pygame.Surface((width, height + THICKNESS), pygame.SRCALPHA)
        edge_rect = pygame.Rect(0, THICKNESS, width, height)
        pygame.draw.rect(final_image, EDGE_COLOR, edge_rect, border_radius = BORDER_RADIUS)

        final_image.blit(scaled_card_back, (0, 0))

        self.card_images["card_back"] = final_image

    def load_audio(self):
        self.music = pygame.mixer.music.load("Audio/lofi_music.mp3")
        pygame.mixer.music.set_volume(0.1)
        self.sounds["click"] = pygame.mixer.Sound("Audio/switch_001.ogg")
        self.sounds["click"].set_volume(0.05)
        self.sounds["deal_card"] = pygame.mixer.Sound("Audio/Card Deal 2.wav")
        self.sounds["deal_card"].set_volume(0.3)
        self.sounds["flip_card"] = pygame.mixer.Sound("Audio/flip_card.wav")
        self.sounds["flip_card"].set_volume(0.15)
        self.sounds["disable_buttons"] = pygame.mixer.Sound("Audio/switch_004.ogg")
        self.sounds["disable_buttons"].set_volume(0.15)
        self.sounds["enable_buttons"] = pygame.mixer.Sound("Audio/switch_005.ogg")
        self.sounds["enable_buttons"].set_volume(0.15)
        self.sounds["player_bust"] = pygame.mixer.Sound("Audio/player_bust.wav")
        self.sounds["player_bust"].set_volume(0.1)
        for i in range(1, 5):
            self.sounds[f"chips_collide_{i}"] = pygame.mixer.Sound(f"Audio/chips-collide-{i}.ogg")
            self.sounds[f"chips_collide_{i}"].set_volume(0.15)

    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def play_music(self):
        pygame.mixer.music.play(-1)

class Game:
    BACKGROUND_COLOR = (47, 101, 77)
    def __init__(self, game_surface):
        self.asset_manager = AssetManager()
        self.asset_manager.play_music()
        self.game_surface = game_surface

        self.deck = Deck(self.asset_manager.card_images, 575, 35)

        self.chips = []
 
        self.chip_pool = []
        self.starting_chips = 20
        self.player_money = 0
        self.max_bet = 10

        self.dealer = Hand([], 212, 100)
        self.dealer.facedown_offset = 125
        self.player = Hand([], 265, 460)

        self.last_deal_time = 0
        self.deal_delay = 250 #250 ms
        self.chip_delay = 100

        self.state = "starting_chips"

        self.current_bet = 1

        self.texts = {
            "bet_display": Text(370, 700, f"${self.current_bet}", text_offset_x=-6),
            "player_money": Text(25, 730, f"Player Total: ${len(self.chips)}"),
            "player_score": Text(370, 425, "", font_size=40),
            "dealer_score": Text(370, 325, "", font_size=40),
        }

        self.buttons = {
            "hit": Button(225, 380, 100, 50, "HIT!", 
                          color = (176, 58, 54), hover_color = (166, 50, 50), 
                          clicked_color = (146, 45, 45), action=self.player_hit, clickable= False),
            "stand": Button(375, 380, 100, 50, "STAND", 
                            color = (176, 58, 54), hover_color = (166, 50, 50), 
                            clicked_color = (146, 45, 45), action=self.player_stand, clickable= False),
            "double": Button(525, 380, 100, 50, "DOUBLE!", 
                             color = (176, 58, 54), hover_color = (166, 50, 50), 
                             clicked_color = (146, 45, 45), action=self.player_double, clickable= False),
            "increase_bet-1": Button(425, 700, 50, 50, "+1", 
                        color = (50, 168, 82), hover_color = (43, 148, 71), 
                        clicked_color = (37, 128, 62), border_radius = 20, travel_distance = 8,
                        font_size = 40, action= lambda: self.increase_bet(1)),
            "decrease_bet-1": Button(325, 700, 50, 50, "-1", 
                        color = (166, 50, 50), hover_color = (146, 45, 45), 
                        clicked_color = (140, 40, 40), border_radius = 20, travel_distance = 8,
                        font_size = 40, action= lambda: self.decrease_bet(1)),
            "increase_bet-5": Button(480, 700, 50, 50, "+5", 
                        color = (50, 168, 82), hover_color = (43, 148, 71), 
                        clicked_color = (37, 128, 62), border_radius = 20, travel_distance = 8,
                        font_size = 40, action= lambda: self.increase_bet(5)),
            "decrease_bet-5": Button(270, 700, 50, 50, "-5", 
                        color = (166, 50, 50), hover_color = (146, 45, 45), 
                        clicked_color = (140, 40, 40), border_radius = 20, travel_distance = 8,
                        font_size = 40, action= lambda: self.decrease_bet(5)),
            "confirm_bet": Button(600, 700, 125, 75, "Confirm Bet", 
                             color = (176, 58, 54), hover_color = (166, 50, 50), 
                             clicked_color = (146, 45, 45), action=self.confirm_bet),
        }

    def deal_starting_cards(self):
        self.texts["dealer_score"].set_text("")
        if len(self.chips) == 0:
            self.state = "lost_game"
            self.texts["player_score"].set_text("Out of money. You Lost!")
            return self.state
        self.current_bet = 1
        self.texts["bet_display"].set_text("$1")
        self.player.cards = []
        self.dealer.cards = []
        self.state = "dealing"
        self.flip_queue = None
        self.deal_queue = [self.player, self.dealer, self.player, self.dealer]
        self.last_deal_time = pygame.time.get_ticks()

    def clear_player_cards(self):
        for card in self.player.cards:
            card.move_to(1000, 375)

    def clear_dealer_cards(self):
        self.current_bet = 1
        self.texts["bet_display"].set_text("$1")
        for card in self.dealer.cards:
            card.move_to(1000, 375)

    def player_hit(self):
        self.deal_to_player()
        self.disable_buttons(["double"])
        self.texts["player_score"].set_text(f"{self.player.get_value()}")
        self.player.cards[-1].flip()
        self.asset_manager.play_sound("deal_card")
        if self.player.get_value() > 21:
            self.player_loss()

    def player_loss(self):
        self.state = "end_of_round"
        self.last_deal_time = pygame.time.get_ticks()
        self.actions = []

        if self.player.get_value() > 21:
            self.texts["player_score"].set_text("Over 21! You busted!")
            self.asset_manager.play_sound("player_bust")
            self.actions.append({"function": self.dealer.cards[1].flip, "time": 1000})
        else:
            self.texts["player_score"].set_text(f"Dealer score of {self.dealer.get_value()} beat your score of {self.player.get_value()}")
        for chip in self.chip_pool:
            self.actions.append({"function": chip.move_offscreen, "time": self.chip_delay})
        self.actions.append({"function": self.clear_chip_pool,  "time": 1})
        self.actions.append({"function": self.clear_player_cards,  "time": 500})
        self.actions.append({"function": self.clear_dealer_cards, "time": 500})
        self.actions.append({"function": self.deal_starting_cards, "time": 1000})

        self.disable_buttons(("hit", "stand", "double", "decrease_bet-1", "increase_bet-1","decrease_bet-5", "increase_bet-5", "confirm_bet"))
        
    def push(self):
        self.state = "end_of_round"
        self.last_deal_time = pygame.time.get_ticks()
        self.texts["player_score"].set_text("Its a tie!")
        self.actions = []
        self.current_bet = 0
        self.actions.append({"function": self.update_chip_pool,  "time": 500})
        self.actions.append({"function": self.clear_player_cards,  "time": 500})
        self.actions.append({"function": self.clear_dealer_cards, "time": 500})
        self.actions.append({"function": self.deal_starting_cards, "time": 1000})

    def player_win(self):
        self.state = "end_of_round"
        self.last_deal_time = pygame.time.get_ticks()
        if self.player.get_value() == 21 and len(self.player) == 2: #blackjack pays 1.5 more
            winnings = round(self.current_bet * 1.5)
        else:
            winnings = self.current_bet
        self.texts["player_score"].set_text(f"You beat the dealer! Winnings: ${self.current_bet}")
        self.actions = []
        self.current_bet = 0
        self.actions.append({"function": self.update_chip_pool,  "time": 500})
        for i in range(winnings):
            self.actions.append({"function": self.add_chip,  "time": self.chip_delay})
        self.actions.append({"function": self.clear_player_cards,  "time": 500})
        self.actions.append({"function": self.clear_dealer_cards, "time": 500})
        self.actions.append({"function": self.deal_starting_cards, "time": 1000})

        self.disable_buttons(("hit", "stand", "double", "decrease_bet-1", "increase_bet-1","decrease_bet-5", "increase_bet-5", "confirm_bet"))

    def player_stand(self):
        self.texts["dealer_score"].set_text(f"Dealer Score: {self.dealer.get_value()}")
        for card in self.dealer.cards[1:]:
            if not card.face_up:
                card.flip()
        self.disable_buttons(("double", "stand", "hit"))
        self.last_deal_time = pygame.time.get_ticks()
        self.state = "player_stand"

    def player_double(self):
        self.current_bet *= 2
        self.update_chip_pool()
        self.deal_to_player()
        self.disable_buttons(["double", "stand", "hit"])
        self.texts["player_score"].set_text(f"{self.player.get_value()}")
        self.player.cards[-1].flip()
        self.asset_manager.play_sound("deal_card")
        if self.player.get_value() > 21:
            self.player_loss()
        else:
            self.player_stand()

    def increase_bet(self, amount):
        if self.player_money < amount:
            amount = self.player_money
        if self.current_bet < self.max_bet:
            self.current_bet += amount
            self.current_bet = min(self.current_bet, self.max_bet)
            self.texts["bet_display"].set_text(f"${self.current_bet}")
            self.update_chip_pool()
        

    def decrease_bet(self, amount):
        if self.current_bet > 1:
            self.current_bet -= amount
            self.current_bet = max(self.current_bet, 1)
            self.texts["bet_display"].set_text(f"${self.current_bet}")
            self.update_chip_pool()

    def update_chip_pool(self): #Handle which chips are moved to betting pool
        self.chip_pool = []
        self.player_money = 0
        for chip in reversed(self.chips):
            if len(self.chip_pool) < self.current_bet:
                self.chip_pool.append(chip)
                chip.move_to(chip.default_pos.x, 750 - chip.default_pos.y)#mirror chip y position when in pot. 
                chip.in_bet = True
            else:
                chip.in_bet = False
                chip.move_to(chip.default_pos.x, chip.default_pos.y)
            if not chip.in_bet:
                self.player_money += 1
        
        self.texts["player_money"].set_text(f"Player Total: ${self.player_money}")

    def add_chip(self):
        self.player_money += 1
        self.texts["player_money"].set_text(f"Player Total: ${self.player_money}")
        self.chips.append(Chip(0,0, self.asset_manager.poker_chip_images[random.randint(0, 35)]))
        self.chips[-1].speed = 35
        default_x = 30 + 50 * (((len(self.chips) - 1)//10)%4)
        default_y = 700 - 3*((len(self.chips)-1)%10) - 100*(((len(self.chips) - 1)//10)//4)
        self.chips[-1].default_pos = pygame.Vector2(default_x, default_y)
        self.chips[-1].move_to(default_x, default_y)
        self.chips[-1].action_on_stop_moving = lambda: self.asset_manager.play_sound(f"chips_collide_{random.randint(1,4)}")
        self.texts["player_money"].set_text(f"Player Total: ${len(self.chips)}")

    def clear_chip_pool(self):
        for chip in self.chip_pool:
            self.chips.remove(chip)
        self.chip_pool = []

    def confirm_bet(self):
        self.state = "flipping"

    def deal_to_player(self): #handle correct start and target coords of card for player
        self.player.cards.append(self.deck.deal_card())
        self.player.cards[-1].pos = pygame.math.Vector2(self.deck.x + int(len(self.deck)*0.25), self.deck.y - int(len(self.deck)*0.25))
        self.player.cards[-1].move_to(len(self.player)*self.player.card_stack_spacing_x + self.player.x, self.player.y)

    def deal_to_dealer(self): #handle correct start and target coords of card for dealer
        self.dealer.cards.append(self.deck.deal_card())
        self.dealer.cards[-1].pos = pygame.math.Vector2(self.deck.x, self.deck.y)
        if len(self.dealer) == 1:
            self.dealer.cards[-1].move_to(self.dealer.x, self.dealer.y)
        else:
            self.dealer.cards[-1].move_to(self.dealer.facedown_offset + self.dealer.x + len(self.dealer)*self.dealer.card_stack_spacing_x, self.dealer.y)

    def update(self, mouse_pos):
        current_time = pygame.time.get_ticks()
        if self.state == "starting_chips":
            if len(self.chips) < self.starting_chips:
                if current_time - self.last_deal_time > self.chip_delay:
                    self.add_chip()
                    self.last_deal_time = current_time
            else:
                self.deal_starting_cards()
        if self.state == "dealing":
            if len(self.deal_queue) > 0:
                if current_time - self.last_deal_time > self.deal_delay:
                    hand = self.deal_queue.pop(0)
                    if hand == self.player:
                        self.deal_to_player()
                    else:
                        self.deal_to_dealer()
                    if len(self.deal_queue) == 0:
                        hand.cards[-1].action_on_stop_moving = self.update_chip_pool
                    self.last_deal_time = current_time
                    self.asset_manager.play_sound("deal_card")
            else:
                self.state = "enable_buttons"
        if self.state == "enable_buttons":
            if current_time - self.last_deal_time > self.deal_delay*2:
                self.enable_buttons(("decrease_bet-1", "increase_bet-1","decrease_bet-5", "increase_bet-5", "confirm_bet"))
                self.texts["player_score"].set_text("Place your bet!")
                self.state = "player_set_bet"
        if self.state == "end_of_round":
            if len(self.actions) > 0:
                action = self.actions[0]
                if current_time - self.last_deal_time > action["time"]:
                    self.last_deal_time = current_time
                    action = self.actions.pop(0)
                    action["function"]()
        if self.state == "player_stand":
            if current_time - self.last_deal_time > self.deal_delay*5:
                dealer_score = self.dealer.get_value()
                if dealer_score < 17:
                    self.deal_to_dealer()
                    dealer_score = self.dealer.get_value()
                    self.texts["dealer_score"].set_text(f"Dealer Score: {dealer_score}")
                    if not self.dealer.cards[-1].face_up:
                        self.dealer.cards[-1].flip()
                    self.last_deal_time = current_time
                elif dealer_score > self.player.get_value() and dealer_score <= 21:
                    self.player_loss()
                elif dealer_score == self.player.get_value():
                    self.push()
                elif dealer_score < self.player.get_value() or dealer_score > 21:
                    self.player_win()
        if self.state == "flipping":
            if self.flip_queue == None:
                self.flip_queue = [self.player.cards, [self.dealer.cards[0]]]
            if len(self.flip_queue) > 0:
                if current_time - self.last_deal_time > self.deal_delay:
                    cards_to_flip = self.flip_queue.pop(0)
                    for card in cards_to_flip:
                        self.last_deal_time = current_time
                        card.flip()
                    self.asset_manager.play_sound("flip_card")
            else:
                self.state = "player_turn"
                self.texts["player_score"].set_text(f"Your Score: {self.player.get_value()}")
                self.enable_buttons(("hit", "stand"))
                if self.current_bet * 2 <= len(self.chips):
                    self.enable_buttons(["double"])
                self.disable_buttons(("decrease_bet-1", "increase_bet-1","decrease_bet-5", "increase_bet-5", "confirm_bet"))
        

        self.mouse_pos = mouse_pos
        for button in self.buttons.values():
            button.update(mouse_pos)

        for chip in self.chips:
            chip.update()

        for card in self.player.cards:
            card.update()

        for card in self.dealer.cards:
            card.update()

    def mouse_down(self):
        for button in self.buttons.values():
            if button.clickable:
                if button.rect.collidepoint(self.mouse_pos):
                    button.color = button.clicked_color
                    button.clicked = True
                    self.asset_manager.play_sound("click")
                    button.frame = button.travel_distance
                else:
                    button.color = button.default_color
                    button.clicked = False
        
    def mouse_up(self):
        for button in self.buttons.values():
            if button.clickable:
                if button.rect.collidepoint(self.mouse_pos):
                    button.color = button.hover_color  
                    button.action()
                else:
                    button.color = button.default_color
                button.clicked = False

    def enable_buttons(self, button_names):
        if len(button_names) > 0:
            self.asset_manager.play_sound("enable_buttons")
        for button in button_names:
            if button != None:
                self.buttons[button].clickable = True

    def disable_buttons(self, button_names):
        if len(button_names) > 0:
            self.asset_manager.play_sound("disable_buttons")

        for button in button_names:
            self.buttons[button].clickable = False

    def draw_player_hand(self):
            for card in self.player.cards:
                card.draw(self.game_surface)

    def draw_dealer_hand(self):
        for card in self.dealer.cards:
            card.draw(self.game_surface)

    def draw_deck(self):
        self.deck.draw(self.game_surface)

    def draw_buttons(self):
        for button in self.buttons.values():
            button.draw(self.game_surface)

    def draw_texts(self):
        for text in self.texts.values():
            text.draw(self.game_surface)
            
    def draw_background(self):
        self.game_surface.fill(Game.BACKGROUND_COLOR)

    def draw_chips(self):
        for chip in self.chips:
            if not chip.in_bet:
                chip.draw(self.game_surface)
        for chip in self.chip_pool:
            chip.draw(self.game_surface)

    def draw(self):
        self.draw_background()
        self.draw_chips()
        self.draw_buttons()
        self.draw_deck()
        self.draw_dealer_hand()
        self.draw_player_hand()
        self.draw_texts()
        
        


def main():
    window_width = 1000
    window_height = 1000
    game_width = 750 #game uses 750x750 coordinate system
    game_height = 750

    pygame.init()

    window = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    game_surface = pygame.Surface((game_width, game_height))
    game = Game(game_surface)
    running = True
    while running:

        mouse_x, mouse_y = pygame.mouse.get_pos() #window coordinates of mouse cursor
        physical_width, physical_height = window.get_size()

        scale_x = physical_width / game_width
        scale_y = physical_height / game_height

        game_x = int(mouse_x / scale_x) #in game coordinates of mouse cursor
        game_y = int(mouse_y / scale_y)
        game.update((game_x, game_y))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                window = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                game.mouse_down()
            elif event.type == pygame.MOUSEBUTTONUP:
                game.mouse_up()
                
        game.draw()  

        scaled_surface = pygame.transform.scale(game_surface, window.get_size())
        window.blit(scaled_surface, (0, 0))

        pygame.display.update()
        clock.tick(60)
    pygame.display.quit()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()