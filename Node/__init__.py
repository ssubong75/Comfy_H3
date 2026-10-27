"""Ratio-dependent resolution presets using ComfyUI's native DynamicCombo."""
from comfy_api.latest import ComfyExtension, io

PRESETS = {
    '16:9': ((1280, 736), (1536, 864), (1728, 960), (1920, 1088), (2304, 1280), (2560, 1440)),
    '9:16': ((736, 1280), (864, 1536), (960, 1728), (1088, 1920), (1280, 2304), (1440, 2560)),
    '2:3': ((832, 1248), (960, 1440), (1024, 1536), (1152, 1728), (1408, 2112), (1600, 2400)),
    '3:2': ((1248, 832), (1440, 960), (1536, 1024), (1728, 1152), (2112, 1408), (2400, 1600)),
    '1:1': ((960, 960), (1152, 1152), (1280, 1280), (1440, 1440), (1728, 1728), (1984, 1984)),
    '21:9': ((1568, 672), (1792, 768), (2016, 864), (2240, 960), (2688, 1152), (3136, 1344)),
    '4:3': ((1152, 864), (1280, 960), (1536, 1152), (1664, 1248), (2048, 1536), (2304, 1728)),
    '3:4': ((864, 1152), (960, 1280), (1152, 1536), (1248, 1664), (1536, 2048), (1728, 2304)),
}

def option_label(width, height):
    return f'{width}×{height} - 약 {width * height / 1_000_000:.2f}MP'

def labels(ratio):
    return [option_label(w, h) for w, h in PRESETS[ratio]]

def selection_input():
    return io.DynamicCombo.Input(
        'ratio', display_name='화면 비율',
        options=[io.DynamicCombo.Option(ratio, inputs=[
            io.Combo.Input('해상도 단계', display_name='해상도 단계',
                           options=labels(ratio), default=labels(ratio)[1]),
        ]) for ratio in PRESETS],
    )

def course_selection_input():
    return io.DynamicCombo.Input(
        'ratio', display_name='화면 비율',
        options=[io.DynamicCombo.Option(ratio, inputs=[
            io.Combo.Input('1코스 해상도', display_name='1코스 해상도 (1~1.6MP)',
                           options=labels(ratio), default=labels(ratio)[2]),
            io.Combo.Input('3코스 해상도', display_name='3코스 해상도 (2~4MP)',
                           options=labels(ratio), default=labels(ratio)[4]),
        ]) for ratio in PRESETS],
    )

def resolve_selection(selection, key='해상도 단계'):
    ratio = selection.get('ratio')
    if ratio not in PRESETS:
        raise ValueError(f'지원하지 않는 화면 비율: {ratio!r}')
    label = selection.get(key)
    choices = labels(ratio)
    if label not in choices:
        raise ValueError(f'{ratio}의 해상도 옵션이 아닙니다: {label!r}')
    index = choices.index(label)
    return PRESETS[ratio][index]

class ResolutionPreset(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='SsubongResolutionPreset',
            display_name='화면 비율 · 해상도', category='ssubong/해상도',
            inputs=[selection_input()],
            outputs=[io.Int.Output('width', display_name='가로'),
                     io.Int.Output('height', display_name='세로')],
        )

    @classmethod
    def execute(cls, ratio):
        return io.NodeOutput(*resolve_selection(ratio))

class QwenResolutionPreset(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='SsubongQwenResolutionPreset',
            display_name='화면 비율 · 해상도 · 생성 개수', category='ssubong/해상도',
            inputs=[selection_input(), io.Int.Input('batch_size', display_name='생성 개수',
                    default=1, min=1, max=4096, step=1)],
            outputs=[io.Latent.Output('latent', display_name='LATENT'),
                     io.Int.Output('save_width', display_name='저장 가로'),
                     io.Int.Output('save_height', display_name='저장 세로'),
                     io.Boolean.Output('resize', display_name='저장 크기 보정')],
        )

    @classmethod
    def execute(cls, ratio, batch_size=1):
        width, height = resolve_selection(ratio)
        from nodes import EmptyLatentImage
        latent = EmptyLatentImage().generate(width, height, batch_size)[0]
        return io.NodeOutput(latent, width, height, False)

class H3ResolutionPreset(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='SsubongH3ResolutionPreset',
            display_name='화면 비율 · 해상도 · 요청 길이',
            category='ssubong/해상도',
            inputs=[selection_input(), io.Float.Input('seconds', display_name='요청 길이 (초·규격 올림)',
                    default=10, min=0.0, max=3600.0, step=0.1)],
            outputs=[io.Int.Output('width', display_name='가로'),
                     io.Int.Output('height', display_name='세로'),
                     io.Int.Output('frames', display_name='프레임 수'),
                     io.Int.Output('save_width', display_name='저장 가로'),
                     io.Int.Output('save_height', display_name='저장 세로')],
        )

    @classmethod
    def execute(cls, ratio, seconds=10):
        width, height = resolve_selection(ratio)
        requested = max(5, round(seconds * 24))
        frames = requested + (5 - (requested % 17)) % 17
        return io.NodeOutput(width, height, frames, width, height)

class H3CourseResolutionPreset(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='SsubongH3CourseResolutionPreset',
            display_name='화면 비율 · 코스별 해상도 (1·2·3코스)',
            category='ssubong/해상도',
            inputs=[course_selection_input()],
            outputs=[io.Int.Output('width_1', display_name='1코스 가로'),
                     io.Int.Output('height_1', display_name='1코스 세로'),
                     io.Int.Output('width_3', display_name='3코스 가로'),
                     io.Int.Output('height_3', display_name='3코스 세로')],
        )

    @classmethod
    def execute(cls, ratio):
        w1, h1 = resolve_selection(ratio, '1코스 해상도')
        w3, h3 = resolve_selection(ratio, '3코스 해상도')
        return io.NodeOutput(w1, h1, w3, h3)


import os
import urllib.request
import torch
import folder_paths
import comfy.model_management
import comfy.utils

MOSS_PRESETS = {
    '16:9': ((1536, 864), (1728, 960), (1920, 1088)),
    '9:16': ((864, 1536), (960, 1728), (1088, 1920)),
    '2:3': ((832, 1248), (1024, 1536), (1152, 1728)),
    '3:2': ((1248, 832), (1536, 1024), (1728, 1152)),
    '1:1': ((960, 960), (1280, 1280), (1440, 1440)),
    '21:9': ((1568, 672), (1792, 768), (2240, 960)),
}

MOSS_MODE_50 = '50스텝 · 고품질 (CFG 3.0 · normal)'
MOSS_MODE_8_DMD = '8스텝 · DMD 고속 (CFG 1.0 · simple)'
MOSS_DMD_LORA_DEFAULT = 'moss_sft_8steps_dmd_lora.safetensors'
MOSS_DMD_LORA_URL = (
    'https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd/resolve/'
    'f95df83b5e90ae91ea412434b3f9b7f1c8c6314f/lora.safetensors'
)


def _ensure_dmd_lora(dmd_lora: str) -> str:
    if folder_paths.get_full_path('loras', dmd_lora) is not None:
        return dmd_lora
    for cand in (MOSS_DMD_LORA_DEFAULT, 'lora.safetensors', 'lora_latest.safetensors'):
        if folder_paths.get_full_path('loras', cand) is not None:
            return cand
    lora_dirs = folder_paths.get_folder_paths('loras')
    target_dir = Path(lora_dirs[0])
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / MOSS_DMD_LORA_DEFAULT
    tmp_file = target_dir / f'{MOSS_DMD_LORA_DEFAULT}.part'
    print(f'[MOSS-DMD] Downloading 8-step DMD LoRA to {target_file} ...')
    req = urllib.request.Request(MOSS_DMD_LORA_URL, headers={'User-Agent': 'ComfyUI-MOSS-DMD/1.0'})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp_file, 'wb') as out:
        while True:
            chunk = resp.read(8 * 1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    os.replace(tmp_file, target_file)
    return MOSS_DMD_LORA_DEFAULT


class MossInput(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='SsubongMossImageInput',
            display_name='MOSS · 비율 · 해상도 · 편집 강도',
            category='ssubong/MOSS',
            description='이미지 연결: img2img. 이미지 노드를 바이패스하거나 연결 해제: T2I / 해상도 프리셋.',
            inputs=[
                io.Vae.Input('vae', optional=True),
                io.DynamicCombo.Input('ratio', display_name='화면 비율', options=[
                    io.DynamicCombo.Option(r, inputs=[
                        io.Combo.Input('해상도 단계', options=[option_label(w, h) for w, h in sizes], default=option_label(*sizes[0]))
                    ]) for r, sizes in MOSS_PRESETS.items()
                ]),
                io.Int.Input('batch_size', display_name='생성 개수', default=1, min=1, max=64),
                io.Float.Input('edit_denoise', display_name='편집 강도 (denoise)', default=0.6, min=0.01, max=1.0, step=0.01),
                io.Image.Input('image', optional=True),
            ],
            outputs=[
                io.Latent.Output('latent'),
                io.Float.Output('denoise'),
                io.Int.Output('width'),
                io.Int.Output('height'),
            ],
        )

    @classmethod
    def execute(cls, ratio, vae=None, batch_size=1, edit_denoise=0.6, image=None):
        sizes = MOSS_PRESETS[ratio['ratio']]
        options = [option_label(w, h) for w, h in sizes]
        width, height = sizes[options.index(ratio['해상도 단계'])]
        if image is None or vae is None:
            latent = torch.zeros([batch_size, 128, height // 16, width // 16],
                                 device=comfy.model_management.intermediate_device())
            denoise = 1.0
        else:
            pixels = comfy.utils.common_upscale(image.movedim(-1, 1), width, height, 'lanczos', 'center').movedim(1, -1)
            latent = vae.encode(pixels[:, :, :, :3])
            latent = comfy.utils.repeat_to_batch_size(latent, batch_size)
            denoise = float(edit_denoise)
        return io.NodeOutput({'samples': latent}, denoise, width, height)


class MossSpeedMode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        lora_list = sorted(set(folder_paths.get_filename_list('loras')) | {
            MOSS_DMD_LORA_DEFAULT,
            'lora.safetensors',
        })
        return io.Schema(
            node_id='SsubongMossSpeedMode',
            display_name='MOSS · 50스텝 / 8스텝(DMD) 모드 선택',
            category='ssubong/MOSS',
            description='50스텝 고품질 모드(CFG 3.0, normal, SLG 활성)와 8스텝 DMD 고속 모드(DMD LoRA 자동 적용, CFG 1.0, simple)를 한 번에 전환합니다.',
            inputs=[
                io.Model.Input('model'),
                io.Combo.Input(
                    'mode',
                    display_name='생성 모드',
                    options=[MOSS_MODE_50, MOSS_MODE_8_DMD],
                    default=MOSS_MODE_50,
                ),
                io.Combo.Input(
                    'dmd_lora',
                    display_name='DMD 8스텝 LoRA',
                    options=lora_list,
                    default=MOSS_DMD_LORA_DEFAULT,
                ),
                io.Float.Input(
                    'dmd_strength',
                    display_name='DMD LoRA 강도',
                    default=1.0,
                    min=0.0,
                    max=2.0,
                    step=0.05,
                ),
            ],
            outputs=[
                io.Model.Output('model', display_name='MODEL'),
                io.Int.Output('steps', display_name='steps'),
                io.Float.Output('cfg', display_name='cfg'),
                io.AnyType.Output('sampler_name', display_name='sampler_name'),
                io.AnyType.Output('scheduler', display_name='scheduler'),
            ],
        )

    @classmethod
    def execute(cls, model, mode=MOSS_MODE_50, dmd_lora=MOSS_DMD_LORA_DEFAULT, dmd_strength=1.0):
        if str(mode).startswith('8스텝'):
            m = model.clone()
            m.model_options = m.model_options.copy()
            m.model_options.pop('sampler_calc_cond_batch_function', None)
            if float(dmd_strength) != 0.0:
                resolved_lora = _ensure_dmd_lora(dmd_lora)
                from nodes import LoraLoaderModelOnly
                m = LoraLoaderModelOnly().load_lora_model_only(m, resolved_lora, float(dmd_strength))[0]
            return io.NodeOutput(m, 8, 1.0, 'euler', 'simple')
        return io.NodeOutput(model, 50, 3.0, 'euler', 'normal')


class ResolutionPresetExtension(ComfyExtension):
    async def get_node_list(self):
        return [
            ResolutionPreset,
            QwenResolutionPreset,
            H3ResolutionPreset,
            H3CourseResolutionPreset,
            MossInput,
            MossSpeedMode,
        ]

async def comfy_entrypoint():
    return ResolutionPresetExtension()
