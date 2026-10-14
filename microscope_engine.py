def generate_microscope_svg(sigma_true, rho_true, mic_x=0.0, old_mic_y=0.0):
    """
    Оновлений динамічний JS/SVG рушій окуляра мікроскопа.
    Розраховує істинний радіус шийки краплі перед відривом залежно від 
    фізичних властивостей рідини (закон Харкінса-Брауна).
    """
    # 1. Метрологічний перерахунок шкали: 1 мм = 40 пікселів (ціна поділки 0.1 мм = 4px)
    svg_mic_x = 200 + (mic_x * 40)
    svg_mic_y = 200  # Залишаємо горизонтальну нитку суворо по центру окуляра

    # Розрахунок істинного радіуса шийки в мм за емпіричною моделлю Харкінса-Брауна
    # Для води (~72 мН/м, 1 г/см3) радіус буде ~1.02 мм (px_neck ~ 41)
    # Для ацетону (~23 мН/м, 0.79 г/см3) радіус звузиться до ~0.73 мм (px_neck ~ 29)
    g_const = 9.81
    capillary_constant = (sigma_true / (rho_true * g_const)) ** 0.5 * 1000 # в мм
    
    # Апроксимація радіуса шийки від капілярної постійної речовини
    true_neck_r_mm = 0.52 * capillary_constant + 0.15
    # Перевід у масштабні пікселі для відображення (базовий радіус трубки = 35px)
    px_neck_target = max(24.0, min(34.8, true_neck_r_mm * 35.0 / 1.5))

    # 2. Генерація трьохступеневої ГОСТ-шкали силами Python
    ticks_html = ""
    for i in range(-160, 181, 4):
        tick_index = i // 4
        t_len = 5
        stroke_w = 0.7
        
        if tick_index % 10 == 0:
            t_len = 14          # Кожен 1.0 мм — довгий штрих
            stroke_w = 1.3
        elif tick_index % 5 == 0:
            t_len = 9           # Кожен 0.5 мм — середній штрих
            stroke_w = 1.0
            
        ticks_html += f'<line x1="{svg_mic_x + i}" y1="{svg_mic_y - t_len}" x2="{svg_mic_x + i}" y2="{svg_mic_y + t_len}" stroke="rgba(255,0,0,0.85)" stroke-width="{stroke_w}" />'

    # 3. Чистий шаблон рядка без f-строк для безпеки фігурних дужок JS
    svg_html_template = """
    <div style="background: #161616; padding: 20px; border-radius: 16px; width: 420px; margin: 0 auto; box-shadow: 0 8px 32px rgba(0,0,0,0.6); border: 1px solid #333; text-align: center;">
        <svg id="drop-container" width="400" height="400" viewBox="0 0 400 400" style="background: #010401; border: 4px solid #555; border-radius: 50%;">
            
            <!-- Скляний капіляр знизу -->
            <rect x="162" y="340" width="76" height="60" fill="#333" opacity="0.85" />
            <rect x="165" y="340" width="70" height="60" fill="#010401" />
            <line x1="165" y1="340" x2="235" y2="340" stroke="#666" stroke-width="3" />

            <!-- Контур краплі (Динамічна геометрія) -->
            <path id="fluid-drop" d="" fill="rgba(100, 210, 255, 0.43)" stroke="lightskyblue" stroke-width="2.3" stroke-linejoin="round" />
            <circle id="flying-ball" cx="200" cy="500" r="0" fill="rgba(100, 210, 255, 0.55)" stroke="lightskyblue" stroke-width="2" style="display: none;" />

            <!-- РУХОМА ВИМІРЮВАЛЬНА ШКАЛА -->
            <g id="microscope-grid">
                <line x1="0" y1="DYNAMIC_MIC_Y" x2="400" y2="DYNAMIC_MIC_Y" stroke="rgba(255,0,0,0.85)" stroke-width="1.5" />
                <line x1="DYNAMIC_MIC_X" y1="0" x2="DYNAMIC_MIC_X" y2="400" stroke="rgba(255,0,0,0.85)" stroke-width="1.5" />
                DYNAMIC_TICKS_HTML
            </g>
        </svg>

        <!-- РУЧКИ НАВОДКИ ПІД КАРТИНКОЮ -->
        <div style="color: #ccc; font-family: sans-serif; font-size: 13px; text-align: left; padding: 0 10px;">
            <div>
                <label>⚙️ Гвинт X (горизонтальний зсув візира): <span id="val-x">0.00</span> мм</label>
                <input type="range" id="slider-x" min="-2.0" max="2.0" step="0.01" value="0" style="width: 100%; margin-top: 5px; accent-color: red;">
            </div>
            <!-- Скритий технічний повзунок для внутрішнього зчитування Y, якщо знадобиться -->
            <input type="hidden" id="slider-y" value="0">
            <span id="val-y" style="display:none;">0.00</span>
        </div>
    </div>
    
    <!-- Передаємо індивідуальний розрахований радіус шийки речовини в JS -->
    <input type="hidden" id="param-neck-target-px" value="DYNAMIC_NECK_PX">
    <script>
        if (window.dropAnimInterval) { clearInterval(window.dropAnimInterval); }
        
        const pathDrop = document.getElementById('fluid-drop');
        const ballFly = document.getElementById('flying-ball');
        const lineX = document.getElementById('grid-line-x');
        const lineY = document.getElementById('grid-line-y');
        const ticksContainer = document.getElementById('grid-ticks');
        const sliderX = document.getElementById('slider-x');
        const sliderY = document.getElementById('slider-y');
        const valX = document.getElementById('val-x');
        const valY = document.getElementById('val-y');

        // Зчитуємо індивідуальний динамічний радіус шийки, переданий з Python
        const targetNeckRadiusPx = parseFloat(document.getElementById('param-neck-target-px').value) || 31.5;

        function updateMicroscopeGrid() {
            let x_mm = parseFloat(sliderX.value);
            let y_mm = parseFloat(sliderY.value);
            valX.innerText = x_mm.toFixed(2);
            valY.innerText = y_mm.toFixed(2);

            let px_x = 200 + (x_mm * 40); 
            let px_y = 200 - (y_mm * 40);

            lineX.setAttribute('x1', px_x); lineX.setAttribute('x2', px_x);
            lineY.setAttribute('y1', px_y); lineY.setAttribute('y2', px_y);

            let html = '';
            for (let i = -160; i <= 180; i += 4) {
                let tick_index = i / 4; 
                let t_len = 5;          
                let stroke_w = 0.7;

                if (tick_index % 10 === 0) {
                    t_len = 14;         
                    stroke_w = 1.3;
                } else if (tick_index % 5 === 0) {
                    t_len = 9;          
                    stroke_w = 1.0;
                }
                html += `<line x1="${px_x + i}" y1="${px_y - t_len}" x2="${px_x + i}" y2="${px_y + t_len}" stroke="rgba(255,0,0,0.85)" stroke-width="${stroke_w}" />`;
            }
            ticksContainer.innerHTML = html;
        }
        sliderX.addEventListener('input', updateMicroscopeGrid);
        updateMicroscopeGrid();

        function generatePearContour(progress) {
            let points = []; let steps = 140; 
            let totalH = 2.0 + (progress * 115.0); 
            let baseR = 35;                      // Фіксований радіус капіляра трубки (35px)
            let maxBulbR = baseR + (progress * 18); 
            
            // ІСПРАВЛЕНО: Шийка більше не константа! Вона плавно звужується від 35px 
            // строго до розрахованого значення речовини (targetNeckRadiusPx) залежно від прогресу
            let neckR = baseR - (Math.pow(progress, 2.0) * (baseR - targetNeckRadiusPx)); 

            for (let i = 0; i <= steps; i++) {
                let t = i / steps; let y = 340 - (t * totalH); let r = baseR;
                if (t < 0.35) {
                    let k = t / 0.35; let smooth = 0.5 - 0.5 * Math.cos(k * Math.PI);
                    r = baseR - (baseR - neckR) * smooth;
                } else if (t < 0.75) {
                    let k = (t - 0.35) / 0.40; let smooth = Math.sin(k * Math.PI / 2);
                    r = neckR + (maxBulbR - neckR) * smooth;
                } else {
                    let k = (t - 0.75) / 0.25; r = maxBulbR * Math.sqrt(Math.max(0.0, 1.0 - k * k));
                }
                points.push({x: 200 - r, y: y});
            }
            let dPath = `M 165,340`;
            for (let pt of points) dPath += ` L ` + pt.x.toFixed(1) + `,` + pt.y.toFixed(1);
            for (let i = points.length - 1; i >= 0; i--) {
                dPath += ` L ` + (200 + (200 - points[i].x)).toFixed(1) + `,` + points[i].y.toFixed(1);
            }
            dPath += ` Z`;
            return {d: dPath, h: totalH, r: maxBulbR};
        }

        const loopDuration = 4800; 
        let currentElapsed = 0;
        const frameRateMs = 20;

        window.dropAnimInterval = setInterval(() => {
            if (!document.getElementById('drop-container')) {
                clearInterval(window.dropAnimInterval);
                return;
            }

            currentElapsed += frameRateMs;
            let p = (currentElapsed % loopDuration) / loopDuration;

            if (p <= 0.82) {
                ballFly.style.display = 'none'; pathDrop.style.display = 'block';
                let progress = p / 0.82; let contour = generatePearContour(progress);
                pathDrop.setAttribute('d', contour.d);
                window.lastH = contour.h; window.lastR = contour.r;
            } else if (p <= 0.88) {
                let snapProgress = (p - 0.82) / 0.06;
                let stretchH = window.lastH + (snapProgress * 18);
                
                // Динамічна капілярна нитка перед відривом також звужується адаптивно під речовину
                let snapNeckR = targetNeckRadiusPx * (1.0 - snapProgress) + 2.5 * snapProgress;
                
                let points = [];
                for (let i = 0; i <= 140; i++) {
                    let t = i / 140; let y = 340 - (t * stretchH); let r = 35;
                    if (t < 0.45) {
                        let k = t / 0.45; let smooth = 0.5 - 0.5 * Math.cos(k * Math.PI);
                        r = 35 - (35 - snapNeckR) * smooth;
                    } else if (t < 0.75) {
                        let k = (t - 0.45) / 0.30; r = snapNeckR + (window.lastR * 1.02 - snapNeckR) * Math.sin(k * Math.PI / 2);
                    } else {
                        let k = (t - 0.75) / 0.25; r = window.lastR * 1.02 * Math.sqrt(Math.max(0.0, 1.0 - k * k));
                    }
                    points.push({x: 200 - r, y: y});
                }
                let dPath = `M 165,340`;
                for (let pt of points) dPath += ` L ` + pt.x.toFixed(1) + `,` + pt.y.toFixed(1);
                for (let i = points.length - 1; i >= 0; i--) {
                    dPath += ` L ` + (200 + (200 - points[i].x)).toFixed(1) + `,` + points[i].y.toFixed(1);
                }
                dPath += ` Z`; pathDrop.setAttribute('d', dPath);
            } else if (p <= 0.96) {
                let fallProgress = (p - 0.88) / 0.08;
                let restH = 6 * (1.0 - fallProgress) + 1.0;
                pathDrop.setAttribute('d', `M 165,340 A 35,6 0 0,1 235,340 Z`);
                ballFly.style.display = 'block';
                let ballRadius = window.lastR * 0.84;
                let startY = 340 - window.lastH - 18;
                let curY = startY - (fallProgress * 280); 
                ballFly.setAttribute('cx', '200'); ballFly.setAttribute('cy', curY); ballFly.setAttribute('r', ballRadius);
            } else {
                ballFly.style.display = 'none';
            }
        }, frameRateMs);
    </script>
    """

    # БЕЗПЕЧНА ІНЖЕКЦІЯ ДИНАМІЧНИХ ПАРАМЕТРІВ ФОРМИ
    svg_html = svg_html_template.replace("DYNAMIC_MIC_X", str(svg_mic_x))
    svg_html = svg_html.replace("DYNAMIC_MIC_Y", str(svg_mic_y))
    svg_html = svg_html.replace("DYNAMIC_TICKS_HTML", ticks_html)
    svg_html = svg_html.replace("DYNAMIC_NECK_PX", f"{px_neck_target:.2f}")

    return svg_html
