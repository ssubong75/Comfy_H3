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

class ResolutionPresetExtension(ComfyExtension):
    async def get_node_list(self):
        return [ResolutionPreset, QwenResolutionPreset, H3ResolutionPreset, H3CourseResolutionPreset]

async def comfy_entrypoint():
    return ResolutionPresetExtension()
