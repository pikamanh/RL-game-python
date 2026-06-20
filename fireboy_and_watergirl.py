import pygame,time
import sys

pygame.init()
pygame.mixer.init()
# إعدادات الشاشة
WIDTH1, HEIGHT1 = 1100, 817
screen = pygame.display.set_mode((WIDTH1, HEIGHT1))
pygame.display.set_caption("Fireboy and Watergirl")
main_screen = pygame.image.load("start.png")  
start_s=pygame.mixer.Sound("sounds/start_s.wav")
# الألوان
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
# الخط
font = pygame.font.Font(None, 120)
start_text = font.render("PLAY", True, BLACK)
start_rect = start_text.get_rect(center=(WIDTH1 //2-10, (HEIGHT1 // 2)+20))
next_level=pygame.image.load("next_level.png")
next_level_rect=pygame.Rect(540,498,next_level.get_width(),next_level.get_height())

current_screen = "start" 
running1 = True
while running1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running1 = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if current_screen == "start" and start_rect.collidepoint(event.pos):
                current_screen = "game"
    if current_screen == "start":
        # رسم الزر
        pygame.draw.rect(screen, GREEN, start_rect)
        screen.blit(start_text, start_rect.topleft)
        start_s.play()
        screen.blit(main_screen, (0, 0))

    elif current_screen == "game":
        WIDTH, HEIGHT = 1100, 817
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("level1")
#الاصوات
        jump_boy=pygame.mixer.Sound("sounds/jump_boy.wav")
        back_sound=pygame.mixer.music.load("sounds/back_sound.mp3")
        dimond=pygame.mixer.Sound("sounds/dimond.wav")
        die=pygame.mixer.Sound("sounds/1.die.wav")
        jump_girl=pygame.mixer.Sound("sounds/jump_girl.wav")
        end_s=pygame.mixer.Sound("sounds/end_s.wav")
        arm_open=pygame.mixer.Sound("sounds/arm_open.wav")
        speed_s=pygame.mixer.Sound("sounds/speed_s.wav")
        pathing_through_door=pygame.mixer.Sound("sounds/pathing through door.wav")
        water_s=pygame.mixer.Sound("sounds/water_s.wav")
        
        pygame.mixer.set_num_channels(3)
        channel1 = pygame.mixer.Channel(0) 
        channel2 = pygame.mixer.Channel(1)
        channel3 = pygame.mixer.Channel(2)
# تحميل الصور
        road1 = pygame.image.load("road1.png")
        back_ground = pygame.image.load("background.png")
        fireboy_door = pygame.image.load("fireboy_door.png")  
        fireboy_door_open = pygame.image.load("open_door.png")  
        watergirl_door = pygame.image.load("watergirl_door.png")  
        watergirl_door_open = pygame.image.load("open_door.png")  
        arm = pygame.image.load("arm.png")
        h_gate = pygame.image.load("h_gate.png")
        v_gate = pygame.image.load("v_gate.png")
        v_gate_open = pygame.image.load("v_gate_open.png")
        open_arm = pygame.image.load("open_arm.png")
        fire_lake = pygame.image.load("o11.png")
        water_lake = pygame.image.load("o21.png")
        green_lake = pygame.image.load("o31.png")
        hero_boy = pygame.image.load("hero_boy/stand1.png")
        hero_girl = pygame.image.load("hero_girl/stand1.png")
        red_jewel = pygame.image.load("red_jewel.png")
        blue_jewel = pygame.image.load("blue_jewel.png")
        button = pygame.image.load("button.png")
        button1 = pygame.image.load("button.png")
        end_green= pygame.image.load("end_green.png")
        h_gate_open=pygame.image.load("h_gate_open.png")
        game_over=pygame.image.load("game_over.png")
        end_orange=pygame.image.load("end_orange.png")
        end_orange1=pygame.image.load("end_orange1.png")
        end_violet=pygame.image.load("end_violet.png")
        next_level=pygame.image.load("next_level.png")
# متغيرات اللاعب الأول
        x, y,height, width,step, moves,moves1 = 60, 790,25, 25,5,0,0
        fireboy_score,watergirl_score = 0,0
        left = False
        right = False
        move_left = [pygame.image.load(f"hero_boy/L{i}.png") for i in range(1, 6)]
        move_right = [pygame.image.load(f"hero_boy/R{i}.png") for i in range(1, 6)]
# متغيرات اللاعب الثاني
        o, p,height1, width1 = 60, 620,25,25
        speed,speed1,gravity,gravity1 = 10.9,10.9,0.55,0.55
        left1 = False
        right1 = False
        move_left1 = [pygame.image.load(f"hero_girl/L{i}.png") for i in range(1, 5)]
        move_right1 = [pygame.image.load(f"hero_girl/R{i}.png") for i in range(1, 5)]
# ألوان
        YELLOW=(255,255,0)
        BROWN = (150, 75, 0)  
# قائمة الجواهر
        red_gems = [(290, 50), (200, 360), (1020, 650), (545, 731)]
        blue_gems = [(60, 130), (700, 390), (550, 556), (775, 731)]
        total_red_gems = 4  
        total_blue_gems = 4
        gem_size = 45
# متغيرات القفز
        is_jumping = False
        is_jumping1 = False
        jump_velocity, jump_velocity1= 8,8 
# تعريف المنصات
        platforms = [
            pygame.Rect(0, 792, 1100, 10),pygame.Rect(10, 680, 350, 20),pygame.Rect(190, 424, 365, 20), pygame.Rect(1020, 710, 50, 20), 
            pygame.Rect(10, 200, 140, 140), pygame.Rect(505, 623, 425, 20),pygame.Rect(10, 540, 70, 20), pygame.Rect(150, 310, 790, 20),
            pygame.Rect(435, 168, 610, 20),pygame.Rect(572, 453, 510, 20), pygame.Rect(10, 568, 460, 20), pygame.Rect(247, 115, 113, 20), 
            pygame.Rect(570, 263, 185, 20),pygame.Rect(132, 454, 50, 20),pygame.Rect(390, 145, 35, 70), ]
# الأبواب
        fireboy_door_rect = pygame.Rect(910, 85, fireboy_door.get_width(), fireboy_door.get_height())
        watergirl_door_rect = pygame.Rect(995, 85, watergirl_door.get_width(), watergirl_door.get_height())
        fireboy_door_opened = False 
        watergirl_door_opened = False  
        arm_opened=False
        hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
        hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
        pygame.mixer.music.play(loops=-1)
        start_time = pygame.time.get_ticks()
        timer_running = True  
        elapsed_time = 0  
        font = pygame.font.Font(None, 60)
        on_platform=False
        def moving_fire():
            global left, right, moves, x, y, jump_velocity, is_jumping,on_platform_fireboy
            keys = pygame.key.get_pressed()
            hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
            on_platform_fireboy = False
            if not is_jumping:
                if keys[pygame.K_UP]:
                    is_jumping = True
                    jump_velocity = 8
                    channel1.play(jump_boy)
            else:
                y -= jump_velocity
                jump_velocity -= gravity
            if keys[pygame.K_LEFT] and x - step > 0:
                x -= step
                left = True
                right = False
                moves = (moves + 1) % len(move_left)
            elif keys[pygame.K_RIGHT] and x + width + step < WIDTH:
                x += step
                right = True
                left = False
                moves = (moves + 1) % len(move_right)
            else:
                right = False
                left = False
                moves = 0
            for platform in platforms:
                if hero_boy_rect.colliderect(platform):  
                    if hero_boy_rect.bottom >= platform.top and hero_boy_rect.top < platform.top:
                        y = platform.top - hero_boy.get_height() 
                        is_jumping = False
                        jump_velocity = 0
                        on_platform_fireboy = True
                        break
                    elif hero_boy_rect.top <= platform.bottom and hero_boy_rect.bottom > platform.bottom:
                        y = platform.bottom + 5 
                        break
            if not on_platform_fireboy and not is_jumping:
                y += gravity
                is_jumping = True
        def moving_girl():
            global left1, right1, o, p, jump_velocity1, is_jumping1, moves1,on_platform_watergirl
            keys = pygame.key.get_pressed()
            hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
            on_platform_watergirl = False
            if not is_jumping1:
                if keys[pygame.K_w]:
                    channel3.play(jump_girl)
                    is_jumping1 = True
                    jump_velocity1 = 8
            else:
                p -= jump_velocity1
                jump_velocity1 -= gravity1
            if keys[pygame.K_a] and o - step > 0:
                o -= step
                left1 = True
                right1 = False
                moves1 = (moves1 + 1) % len(move_left1)
            elif keys[pygame.K_d] and o + width1 + step < WIDTH:
                o += step
                right1 = True
                left1 = False
                moves1 = (moves1 + 1) % len(move_right1)
            else:
                right1 = False
                left1 = False
                moves1 = 0
            for platform in platforms:
                if hero_girl_rect.colliderect(platform):
                    if hero_girl_rect.bottom >= platform.top and hero_girl_rect.top < platform.top:
                        p = platform.top - hero_girl.get_height() 
                        is_jumping1 = False
                        jump_velocity1 = 0
                        on_platform_watergirl = True
                        break
                    elif hero_girl_rect.top <= platform.bottom and hero_girl_rect.bottom > platform.bottom:
                        p = platform.bottom + 5 
                        break
            if not on_platform_watergirl and not is_jumping1:
                p += gravity1
                is_jumping1 = True
        def draw_fireboy():
            if left:
             screen.blit(move_left[moves], (x, y))
            elif right:
                screen.blit(move_right[moves], (x, y))
            else:
                screen.blit(hero_boy, (x, y))
        def draw_watergirl():
            if left1:
                screen.blit(move_left1[moves1], (o, p))
            elif right1:
                screen.blit(move_right1[moves1], (o, p))
            else:
                screen.blit(hero_girl, (o, p))
        def gems():
            global fireboy_score,watergirl_score
            hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
            hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
            for gem in red_gems[:]:
                gem_rect = pygame.Rect(gem[0], gem[1], red_jewel.get_width(), red_jewel.get_height())
                if hero_boy_rect.colliderect(gem_rect):
                    red_gems.remove(gem)
                    channel2.play(dimond)
                    fireboy_score += 1
            for gem in blue_gems[:]:
                gem_rect = pygame.Rect(gem[0], gem[1], blue_jewel.get_width(), blue_jewel.get_height())
                if hero_girl_rect.colliderect(gem_rect):
                    blue_gems.remove(gem)
                    channel3.play(dimond)
                    watergirl_score += 1
        def draw_gems():
            for gem in red_gems:
                screen.blit(red_jewel, (gem[0], gem[1]))
            for gem in blue_gems:
                screen.blit(blue_jewel, (gem[0], gem[1]))
# الحلقة الرئيسية
        def play():
            global x, y, o, p,red_gems, blue_gems, gem_size,left, left1, right, right1, moves, moves1,on_platform_watergirl
            global fireboy_score, watergirl_score,fireboy_door_opened, watergirl_door_opened,arm_opened, on_platform_fireboy,current_screen
            global is_jumping, is_jumping1, jump_velocity1, jump_velocity,timer_running,total_blue_gems,total_red_gems
            running = True
            while running:
                pygame.time.delay(3)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running=False
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if current_screen == "game" and next_level_rect.collidepoint(event.pos):
                            current_screen = "level2"
                moving_fire()
                moving_girl()
                for platform in platforms:
                    pygame.draw.rect(screen, BROWN, platform)
                screen.blit(back_ground, (0, 0)) 
                screen.blit(road1, (0, 0))
                screen.blit(fire_lake, (510, 790))
                screen.blit(water_lake, (742, 790))
                screen.blit(green_lake, (684, 617))
                screen.blit(button, (300, 406))
                screen.blit(button1, (850, 294))
                
                fireboy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
                if fireboy_rect.colliderect(fireboy_door_rect):
                    fireboy_door_opened = True  
                watergirl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
                if watergirl_rect.colliderect(watergirl_door_rect):
                    watergirl_door_opened = True  
                if fireboy_door_opened:
                    screen.blit(fireboy_door_open, (910, 85))  
                else:
                    screen.blit(fireboy_door, (910, 85))  
                if watergirl_door_opened:
                    screen.blit(watergirl_door_open, (995, 85))  
                else:
                    screen.blit(watergirl_door, (995, 85))  
                draw_fireboy()
                draw_watergirl()
                gems()
                draw_gems()
                hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
                hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
                if not arm_opened:  
                    screen.blit(v_gate,(155,475))
                    screen.blit(arm, (270, 525))
                    arm_rect = pygame.Rect(270, 520, arm.get_width(), arm.get_height()-5)
                if hero_boy_rect.colliderect(arm_rect) or hero_girl_rect.colliderect(arm_rect):
                    arm_open.play()
                    arm_opened = True  
                if arm_opened:
                    screen.blit(open_arm, (260, 515))  
                    screen.blit(v_gate_open,(155,497+v_gate.get_height()))  
                button_rect = pygame.Rect(300, 406, button.get_width(), button.get_height())
                button1_rect = pygame.Rect(850, 294, button1.get_width(), button1.get_height())
                h_gate_rect = pygame.Rect(987, 310, h_gate.get_width(), h_gate.get_height())
                if hero_boy_rect.colliderect(button_rect) or hero_girl_rect.colliderect(button_rect) or\
                hero_boy_rect.colliderect(button1_rect) or hero_girl_rect.colliderect(button1_rect):
                    if h_gate_rect.y < 390:  
                        h_gate_rect.y += 75
                        screen.blit(h_gate_open, (987, h_gate_rect.y))
                elif h_gate_rect.y==310:
                    screen.blit(h_gate, (987, h_gate_rect.y))
                if hero_boy_rect.colliderect(h_gate_rect):  
                    if hero_boy_rect.bottom >= h_gate_rect.top and hero_boy_rect.top < h_gate_rect.top:
                        y = h_gate_rect.y - hero_boy.get_height() 
                        is_jumping = False
                        jump_velocity = 0
                        on_platform_fireboy = True 
                if not on_platform_fireboy and not is_jumping:
                    y += gravity
                    is_jumping = True
                    
                if hero_girl_rect.colliderect(h_gate_rect):  
                    if hero_girl_rect.bottom >= h_gate_rect.top and hero_girl_rect.top < h_gate_rect.top:
                        p = h_gate_rect.y - hero_boy.get_height() 
                        is_jumping1 = False
                        jump_velocity1 = 0
                        on_platform_watergirl = True    
                if not on_platform_watergirl and not is_jumping1:
                    p += gravity1
                    is_jumping1 = True             
            # المناطق القاتلة
                fire_lake_rect = pygame.Rect(518, 792, fire_lake.get_width()-45, fire_lake.get_height()-18)
                water_lake_rect = pygame.Rect(758, 792, water_lake.get_width()-45, water_lake.get_height()-18)
                fire_lake_rect1 = pygame.Rect(510, 783, fire_lake.get_width()-20, fire_lake.get_height()-16)
                water_lake_rect1 = pygame.Rect(742, 783, water_lake.get_width()-20, water_lake.get_height()-16)
                green_lake_rect = pygame.Rect(686, 622, green_lake.get_width()-45, green_lake.get_height()-17)
                if hero_boy_rect.colliderect(water_lake_rect) or hero_girl_rect.colliderect(fire_lake_rect) or\
                    hero_boy_rect.colliderect(green_lake_rect) or hero_girl_rect.colliderect(green_lake_rect):  
                    timer_running = False
                    pygame.mixer.music.stop()   
                    channel2.play(end_s) 
                    time.sleep(end_s.get_length())
                    screen.blit(game_over,(145,170))
                    running=False   
                if hero_girl_rect.colliderect(water_lake_rect1) or hero_boy_rect.colliderect(fire_lake_rect1) :  
                    water_s.play()
            #التايمر
                if timer_running:
                    current_time = pygame.time.get_ticks()
                    elapsed_time = (current_time - start_time) // 1000  
                    minutes = elapsed_time // 60  
                    seconds = elapsed_time % 60
                    timer_text = font.render(f" {minutes:02}:{seconds:02}", True, YELLOW)
                    screen.blit(timer_text, (480, 0))
                if elapsed_time>60:
                        pygame.mixer.music.stop()
                        speed_s.play()       
            #شاشة الفوز    
                if fireboy_door_opened and watergirl_door_opened:
                    channel1.play(pathing_through_door)
                    timer_running = False
                    if elapsed_time<90 and fireboy_score==total_red_gems and watergirl_score==total_blue_gems:
                        screen.blit(end_green,(145,170))
                        speed_s.stop()
                        end_s.play()    
                    if elapsed_time<90 and fireboy_score!=total_red_gems or watergirl_score!=total_blue_gems:
                        screen.blit(end_orange,(145,170))
                        speed_s.stop()
                        end_s.play()   
                    if elapsed_time>90 and fireboy_score==total_red_gems and watergirl_score==total_blue_gems:
                        screen.blit(end_orange1,(145,170))
                        speed_s.stop()
                        end_s.play()
                    if elapsed_time>90 and fireboy_score!=total_red_gems or watergirl_score!=total_blue_gems:
                        screen.blit(end_violet,(145,170))
                        speed_s.stop()
                        end_s.play() 
                    screen.blit(next_level, (540,498))
                    if current_screen=="level2":
                       running=False
                pygame.display.flip()

        if __name__ == '__main__':
            play() 
        
        pygame.quit()
     
           
    if current_screen == "level2":
        pygame.init()
        pygame.mixer.init()
        WIDTH, HEIGHT = 1103, 817
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Level 2")
        # الأصوات

        jump_boy = pygame.mixer.Sound("sounds/jump_boy.wav")
        back_sound = pygame.mixer_music.load("sounds/back_sound.mp3")
        speed_s=pygame.mixer.Sound("sounds/speed_s.wav")
        dimond=pygame.mixer.Sound("sounds/dimond.wav")
        die=pygame.mixer.Sound("sounds/1.die.wav")
        pathing_through_door=pygame.mixer.Sound("sounds/pathing through door.wav")
        jump_girl=pygame.mixer.Sound("sounds/jump_girl.wav")
        end_s=pygame.mixer.Sound("sounds/end_s.wav")
        arm_open=pygame.mixer.Sound("sounds/arm_open.wav")
        rolling=pygame.mixer.Sound("sounds/rolling.wav")
        pygame.mixer.set_num_channels(3)
        channel1 = pygame.mixer.Channel(0) 
        channel2 = pygame.mixer.Channel(1)
        channel3 = pygame.mixer.Channel(2) 

        # تحميل الصور
        background = pygame.image.load("background2.png")
        road2 = pygame.image.load("road2.png")
        hero_boy = pygame.image.load("hero_boy/stand1.png")
        hero_girl = pygame.image.load("hero_girl/stand1.png")
        red_jewel = pygame.image.load("red_jewel.png")
        blue_jewel = pygame.image.load("blue_jewel.png")
        fireboy_door = pygame.image.load("fireboy_door2.png")
        fireboy_door_open = pygame.image.load("open_door2.png")
        watergirl_door = pygame.image.load("watergirl_door2.png")
        watergirl_door_open = pygame.image.load("open_door2.png")
        box = pygame.image.load("box.png")
        arm2=pygame.image.load("arm2.png")
        open_arm2=pygame.image.load("open_arm2.png")
        button2 = pygame.image.load("button2.png")
        bink_l=pygame.image.load("bink_L.png")
        bink_r=pygame.image.load("bink_R.png")
        open_green_r=pygame.image.load("open_green_R.png")
        open_green_l=pygame.image.load("open_green_L.png")
        green_r=pygame.image.load("green_r.png")
        green_l=pygame.image.load("green_l.png")
        white_r=pygame.image.load("white_R.png")
        white_r1=pygame.image.load("white_R1.png")
        red_d_r=pygame.image.load("red_d_r.png")
        red_u_l=pygame.image.load("red_u_l.png")
        v_gate = pygame.image.load("v_gate.png")
        v_gate_open=pygame.image.load("v_gate_open.png")
        end_green= pygame.image.load("end_green.png")
        game_over=pygame.image.load("game_over.png")
        end_orange=pygame.image.load("end_orange.png")
        end_orange1=pygame.image.load("end_orange1.png")
        end_violet=pygame.image.load("end_violet.png")
        start_time = pygame.time.get_ticks()  
        timer_running = True  
        elapsed_time = 0
        # متغيرات اللاعب الأول 
        x, y,height, width,step, moves,moves1 = 530, 780,25, 25,5,0,0
        fireboy_score,watergirl_score = 0,0
        left = False
        right = False
        move_left = [pygame.image.load(f"hero_boy/L{i}.png") for i in range(1, 6)]
        move_right = [pygame.image.load(f"hero_boy/R{i}.png") for i in range(1, 6)]
        hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())

        # متغيرات اللاعب الثاني 
        o, p,height1, width1 = 480, 780,25,25
        speed,speed1,gravity,gravity1 = 10.9,10.9,0.55,0.55
        left1 = False
        right1 = False
        move_left1 = [pygame.image.load(f"hero_girl/L{i}.png") for i in range(1, 5)]
        move_right1 = [pygame.image.load(f"hero_girl/R{i}.png") for i in range(1, 5)]
        fireboy_door_opened = False 
        watergirl_door_opened = False 
        hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
        # متغيرات القفز
        is_jumping = False
        is_jumping1 = False
        jump_velocity,jump_velocity1 = 8,8

        # تعريف المنصات
        platforms = [
            pygame.Rect(0, 790, 1103, 10),pygame.Rect(55, 650, 490, 25), pygame.Rect(590, 710, 40, 20),pygame.Rect(880, 170, 170, 20),  
            pygame.Rect(0, 227, 450, 20), pygame.Rect(702, 540, 400, 20),  pygame.Rect(15, 455, 70, 20), pygame.Rect(770, 284, 330, 20),  
            pygame.Rect(583, 115, 240, 20), pygame.Rect(563, 368, 150, 20), pygame.Rect(132, 509, 550, 23), pygame.Rect(190, 400, 100, 20), 
            pygame.Rect(455, 205, 115, 20),pygame.Rect(850, 380, 300, 40)]
        # قائمة الجواهر
        red_gems = [(135, 150), (285, 330), (95, 560), (350, 720), (650, 50), (910, 220)]
        blue_gems = [(300, 150), (145, 330), (80, 726), (650, 641), (910, 100), (865, 460)]
        gem_size = 45
        total_red_gems = 6  
        total_blue_gems = 6
        # الأبواب
        fireboy_door_rect = pygame.Rect(365, 138, fireboy_door.get_width(), fireboy_door.get_height())
        watergirl_door_rect = pygame.Rect(40, 138, watergirl_door.get_width(), watergirl_door.get_height())
        fireboy_door_opened = False
        watergirl_door_opened = False
        # الألوان
        YELLOW=(255,255,0)
        GREEN = (0, 255, 0)
        box_speed,box_gravity = 30 ,3
        box_falling = False  
        hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
        hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
        box_rect = pygame.Rect(828, 235, box.get_width(), box.get_height())
        def update_box():
            global box_falling
            global hero_boy_rect,hero_girl_rect,box_rect
            
            on_platform = False
            for platform in platforms:
                if box_rect.colliderect(platform): 
                    on_platform = True
                    break
            if not on_platform:
                box_falling = True
            else:
                box_falling = False
            if box_falling:
                box_rect.y += box_gravity
            if hero_boy_rect.colliderect(box_rect):
                rolling.play()
                if right:
                    box_rect.x += box_speed 
                elif left:
                    box_rect.x -= box_speed 
            if hero_girl_rect.colliderect(box_rect):
                rolling.play()
                if right1:
                    box_rect.x += box_speed 
                elif left1:
                    box_rect.x -= box_speed 
            if box_rect.x + box_rect.width > WIDTH:
                        box_rect.x = WIDTH - box_rect.width
        def moving_fire():
            global left, right, moves, x, y, jump_velocity, is_jumping
            keys = pygame.key.get_pressed()
            hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
            on_platform_fireboy = False
            if not is_jumping:
                if keys[pygame.K_UP]:
                    is_jumping = True
                    jump_velocity = 8
                    channel1.play(jump_boy)
            else:
                y -= jump_velocity
                jump_velocity -= gravity
            if keys[pygame.K_LEFT] and x - step > 0:
                x -= step
                left = True
                right = False
                moves = (moves + 1) % len(move_left)
            elif keys[pygame.K_RIGHT] and x + width + step < WIDTH:
                x += step
                right = True
                left = False
                moves = (moves + 1) % len(move_right)
            else:
                right = False
                left = False
                moves = 0
            for platform in platforms:
                if hero_boy_rect.colliderect(platform):  
                    if hero_boy_rect.bottom >= platform.top and hero_boy_rect.top < platform.top:
                        y = platform.top - hero_boy.get_height() 
                        is_jumping = False
                        jump_velocity = 0
                        on_platform_fireboy = True
                        break
                    elif hero_boy_rect.top <= platform.bottom and hero_boy_rect.bottom > platform.bottom:
                        y = platform.bottom + 5 
                        break
            if not on_platform_fireboy and not is_jumping:
                y += gravity
                is_jumping = True
        def moving_girl():
            global left1, right1, o, p, jump_velocity1, is_jumping1, moves1
            keys = pygame.key.get_pressed()
            hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
            on_platform_watergirl = False
            if not is_jumping1:
                if keys[pygame.K_w]:
                    channel3.play(jump_girl)
                    is_jumping1 = True
                    jump_velocity1 = 8
            else:
                p -= jump_velocity1
                jump_velocity1 -= gravity1
            if keys[pygame.K_a] and o - step > 0:
                o -= step
                left1 = True
                right1 = False
                moves1 = (moves1 + 1) % len(move_left1)
            elif keys[pygame.K_d] and o + width1 + step < WIDTH:
                o += step
                right1 = True
                left1 = False
                moves1 = (moves1 + 1) % len(move_right1)
            else:
                right1 = False
                left1 = False
                moves1 = 0
            for platform in platforms:
                if hero_girl_rect.colliderect(platform):
                    if hero_girl_rect.bottom >= platform.top and hero_girl_rect.top < platform.top:
                        p = platform.top - hero_girl.get_height() 
                        is_jumping1 = False
                        jump_velocity1 = 0
                        on_platform_watergirl = True
                        break
                    elif hero_girl_rect.top <= platform.bottom and hero_girl_rect.bottom > platform.bottom:
                        p = platform.bottom + 5 
                        break
            if not on_platform_watergirl and not is_jumping1:
                p += gravity1
                is_jumping1 = True
        def draw_fireboy():
            if left:
                screen.blit(move_left[moves], (x, y))
            elif right:
                screen.blit(move_right[moves], (x, y))
            else:
                screen.blit(hero_boy, (x, y))
        def draw_watergirl():
            if left1:
                screen.blit(move_left1[moves1], (o, p))
            elif right1:
                screen.blit(move_right1[moves1], (o, p))
            else:
                screen.blit(hero_girl, (o, p))
        def gems():
            global fireboy_score,watergirl_score
            hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
            hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
            for gem in red_gems[:]:
                gem_rect = pygame.Rect(gem[0], gem[1], red_jewel.get_width(), red_jewel.get_height())
                if hero_boy_rect.colliderect(gem_rect):
                    red_gems.remove(gem)
                    channel2.play(dimond)
                    fireboy_score += 1
            for gem in blue_gems[:]:
                gem_rect = pygame.Rect(gem[0], gem[1], blue_jewel.get_width(), blue_jewel.get_height())
                if hero_girl_rect.colliderect(gem_rect):
                    blue_gems.remove(gem)
                    channel3.play(dimond)
                    watergirl_score += 1
        def draw_gems():
            for gem in red_gems:
                screen.blit(red_jewel, (gem[0], gem[1]))
            for gem in blue_gems:
                screen.blit(blue_jewel, (gem[0], gem[1]))
        # متغيرات البوابات
        bink_l_rect = pygame.Rect(8, 670, bink_l.get_width(), bink_l.get_height())
        bink_r_rect = pygame.Rect(1050, 670, bink_r.get_width(), bink_r.get_height())
        green_l_rect = pygame.Rect(7, 480, open_green_l.get_width(), open_green_l.get_height())
        green_r_rect = pygame.Rect(1050, 30, open_green_r.get_width(), open_green_r.get_height())
        white_r_rect = pygame.Rect(1050, 175, white_r.get_width(), white_r.get_height())
        white_r1_rect = pygame.Rect(1050, 420, white_r1.get_width(),white_r1.get_height())
        red_u_l_rect = pygame.Rect(215, 110, red_u_l.get_width(), red_u_l.get_height())
        red_d_r_rect = pygame.Rect(215, 280, red_d_r.get_width(), red_d_r.get_height())

        last_portal_teleport,teleport_cooldown = 0,1000
        last_portal_teleport1,teleport_cooldown1 = 0,1000
        last_portal_teleport2,teleport_cooldown2= 0,1000
        last_portal_teleport3,teleport_cooldown3 = 0,1000

        def teleport_player_bink(player_rect, bink_l_rect, bink_r_rect):
            global last_portal_teleport
            current_time = pygame.time.get_ticks()
            if player_rect.colliderect(bink_l_rect) and current_time - last_portal_teleport > teleport_cooldown:
                last_portal_teleport = current_time
                return pygame.Rect(bink_r_rect.x,bink_r_rect.y, player_rect.width,player_rect.height)
            elif player_rect.colliderect(bink_r_rect) and current_time - last_portal_teleport > teleport_cooldown:
                last_portal_teleport = current_time
                return pygame.Rect(bink_l_rect.x,bink_l_rect.y, player_rect.width,player_rect.height)
            return player_rect
        def teleport_player_green(player_rect,green_l_rect,green_r_rect):
            global last_portal_teleport1,teleport_cooldown1
            current_time1 = pygame.time.get_ticks()
            if player_rect.colliderect(green_l_rect) and current_time1 - last_portal_teleport1 > teleport_cooldown1:
                last_portal_teleport1 = current_time1
                return pygame.Rect(green_r_rect.x,green_r_rect.y, player_rect.width,player_rect.height)
            elif player_rect.colliderect(green_r_rect) and current_time1 - last_portal_teleport1 > teleport_cooldown1:
                last_portal_teleport1 = current_time1
                return pygame.Rect(green_l_rect.x,green_l_rect.y, player_rect.width,player_rect.height)
            return player_rect
        def teleport_player_white(player_rect,white_r_rect,white_r1_rect):
            global last_portal_teleport2,teleport_cooldown2
            current_time2 = pygame.time.get_ticks()
            if player_rect.colliderect(white_r_rect) and current_time2 - last_portal_teleport2 > teleport_cooldown2:
                last_portal_teleport2 = current_time2
                return pygame.Rect(white_r1_rect.x,white_r1_rect.y, player_rect.width,player_rect.height)
            elif player_rect.colliderect(white_r1_rect) and current_time2 - last_portal_teleport2 > teleport_cooldown2:
                last_portal_teleport2 = current_time2
                return pygame.Rect(white_r_rect.x,white_r_rect.y, player_rect.width,player_rect.height)
            return player_rect
        def teleport_player_red(player_rect,red_d_r_rect,red_u_l_rect):
            global last_portal_teleport3,teleport_cooldown3
            current_time3 = pygame.time.get_ticks()
            if player_rect.colliderect(red_d_r_rect) and current_time3 - last_portal_teleport3 > teleport_cooldown3:
                last_portal_teleport3 = current_time3
                return pygame.Rect(red_u_l_rect.x,red_u_l_rect.y, player_rect.width,player_rect.height)
            elif player_rect.colliderect(red_u_l_rect) and current_time3 - last_portal_teleport3 > teleport_cooldown3:
                last_portal_teleport3 = current_time3
                return pygame.Rect(red_d_r_rect.x,red_d_r_rect.y, player_rect.width,player_rect.height)
            return player_rect
        arm2_opened = False  
        button2_opened=False
        pygame.mixer.music.play(loops=-1)
        def main():
            global red_gems, blue_gems, fireboy_score, watergirl_score,arm2_opened,button2_opened
            global x,y,o,p,hero_boy_rect,hero_girl_rect,fireboy_door_opened,watergirl_door_opened
            global timer_running
            running2 = True
            while running2:
                pygame.time.delay(3)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running2 = False

                for platform in platforms:
                    pygame.draw.rect(screen, YELLOW, platform)
                screen.blit(background, (0, 0))
                screen.blit(button2,(930,520))
                button2_rect=pygame.Rect(930,520,button2.get_width(),button2.get_height())
                if hero_boy_rect.colliderect(button2_rect) or hero_girl_rect.colliderect(button2_rect) or box_rect.colliderect(button2_rect):
                    button2_opened=True
                if not hero_boy_rect.colliderect(button2_rect) and hero_girl_rect.colliderect(button2_rect) and box_rect.colliderect(button2_rect):
                    button2_opened=False
                if not button2_opened:
                    screen.blit(v_gate,(630,422))
                if button2_opened:
                    screen.blit(v_gate_open,(630,440+v_gate.get_height()))
                screen.blit(road2, (0, 0))
                screen.blit(box, box_rect.topleft)
                gems()
                draw_gems()
                moving_fire()
                moving_girl()
                hero_boy_rect = pygame.Rect(x, y, hero_boy.get_width(), hero_boy.get_height())
                hero_girl_rect = pygame.Rect(o, p, hero_girl.get_width(), hero_girl.get_height())
                if hero_boy_rect.colliderect(fireboy_door_rect):
                    fireboy_door_opened = True  
                if hero_girl_rect.colliderect(watergirl_door_rect):
                    watergirl_door_opened = True  

                if fireboy_door_opened:
                    screen.blit(fireboy_door_open, (365, 138))  
                else:
                    screen.blit(fireboy_door, (365, 138)) 
                if watergirl_door_opened:
                    screen.blit(watergirl_door_open, (40, 138))  
                else:
                    screen.blit(watergirl_door, (40, 138)) 
                draw_fireboy()
                draw_watergirl()
                update_box()
                
                new_hero_boy_rect=teleport_player_bink(hero_boy_rect, bink_l_rect, bink_r_rect)
                new_hero_girl_rect=teleport_player_bink(hero_girl_rect, bink_l_rect, bink_r_rect)
                
                if new_hero_boy_rect != hero_boy_rect:
                    x, y = new_hero_boy_rect.x, new_hero_boy_rect.y
                    hero_boy_rect = new_hero_boy_rect
                if new_hero_girl_rect != hero_girl_rect:
                    o, p = new_hero_girl_rect.x, new_hero_girl_rect.y
                    hero_girl_rect = new_hero_girl_rect

                new_hero_boy_rect1=teleport_player_green(new_hero_boy_rect, green_l_rect, green_r_rect)
                new_hero_girl_rect1=teleport_player_green(new_hero_girl_rect, green_l_rect, green_r_rect)
                if new_hero_boy_rect1 != new_hero_boy_rect:
                    x, y = new_hero_boy_rect1.x, new_hero_boy_rect1.y
                    new_hero_boy_rect = new_hero_boy_rect1
                if new_hero_girl_rect1 != new_hero_girl_rect:
                    o, p = new_hero_girl_rect1.x, new_hero_girl_rect1.y
                    new_hero_girl_rect = new_hero_girl_rect1

                new_hero_boy_rect2=teleport_player_white(new_hero_boy_rect1, white_r_rect, white_r1_rect)
                new_hero_girl_rect2=teleport_player_white(new_hero_girl_rect1, white_r_rect, white_r1_rect)
                box_rect1=teleport_player_white(box_rect, white_r_rect, white_r1_rect)
                if new_hero_boy_rect2 != new_hero_boy_rect1:
                    x, y = new_hero_boy_rect2.x, new_hero_boy_rect2.y
                    new_hero_boy_rect1 = new_hero_boy_rect2
                if new_hero_girl_rect2 != new_hero_girl_rect1:
                    o, p = new_hero_girl_rect2.x, new_hero_girl_rect2.y
                    new_hero_girl_rect1 = new_hero_girl_rect2
                if box_rect1 != box_rect:
                    box_rect.x, box_rect.y = box_rect1.x-15, box_rect1.y
                
                new_hero_boy_rect3=teleport_player_red(new_hero_boy_rect2, red_d_r_rect, red_u_l_rect)
                new_hero_girl_rect3=teleport_player_red(new_hero_girl_rect2, red_d_r_rect,red_u_l_rect)
                if new_hero_boy_rect3 != new_hero_boy_rect2:
                    x, y = new_hero_boy_rect3.x, new_hero_boy_rect3.y
                    new_hero_boy_rect2 = new_hero_boy_rect3
                if new_hero_girl_rect3 != new_hero_girl_rect2:
                    o, p = new_hero_girl_rect3.x, new_hero_girl_rect3.y
                    new_hero_girl_rect2 = new_hero_girl_rect3
                # تشغيل البوابة الخضراء
                if not arm2_opened:  
                    screen.blit(arm2, (412, 618))
                    screen.blit(green_l,(7,480))
                    screen.blit(green_r,(1050,30))
                arm2_rect = pygame.Rect(412, 618, arm2.get_width(), arm2.get_height())
                if hero_boy_rect.colliderect(arm2_rect) or hero_girl_rect.colliderect(arm2_rect):
                    arm_open.play()
                    arm2_opened = True  
                if arm2_opened:
                    screen.blit(open_arm2, (412, 618))  
                    screen.blit(open_green_l,(7,480))
                    screen.blit(open_green_r,(1050,30))
                # رسم العناصر
                screen.blit(bink_l,(7,670))
                screen.blit(bink_r,(1050,670))
                screen.blit(white_r,(1050,175))
                screen.blit(white_r1,(1050,420))
                screen.blit(red_d_r,(215,280))
                screen.blit(red_u_l,(215,110))
                #شاشات الفوز
                if fireboy_door_opened and watergirl_door_opened:
                    timer_running = False
                    if elapsed_time<=90 and fireboy_score==total_red_gems and watergirl_score==total_blue_gems:
                        screen.blit(end_green,(145,170))
                        speed_s.stop()
                        end_s.play() 
                    if elapsed_time<=90 and fireboy_score!=6 or watergirl_score!=6:
                        screen.blit(end_orange,(145,170))
                        speed_s.stop()
                        end_s.play() 
                    if elapsed_time>90 and fireboy_score==total_red_gems and watergirl_score==total_blue_gems:
                        screen.blit(end_orange1,(145,170))
                        speed_s.stop()
                        end_s.play() 
                    if elapsed_time>90 and fireboy_score!=6 or watergirl_score!=6:
                        screen.blit(end_violet,(145,170))
                        speed_s.stop()
                        end_s.play()
                #التايمر 
                font = pygame.font.Font(None, 60)
                if timer_running:
                    current_time = pygame.time.get_ticks()
                    elapsed_time = (current_time - start_time) // 1000 
                    minutes = elapsed_time // 60  
                    seconds = elapsed_time % 60
                    timer_text = font.render(f" {minutes:02}:{seconds:02}", True, YELLOW)
                    screen.blit(timer_text, (490, 0))
                if elapsed_time>60:
                    pygame.mixer.music.stop()
                    speed_s.play()               
                pygame.display.update()
            pygame.quit()
            sys.exit()
        if __name__ == '__main__':
            main()    
    pygame.display.flip()
pygame.quit()
sys.exit()
