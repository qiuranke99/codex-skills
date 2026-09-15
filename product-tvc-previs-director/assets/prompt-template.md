生成一段总时长{{duration_seconds}}秒、{{aspect_ratio}}画幅、{{visual_intent}}的产品广告。

全片共{{shot_count}}个镜头。{{edit_structure}}
转场、变速和最终停留均计入总时长。

## 输入包含

A. 产品参考图：{{product_reference_ids}}
作为{{product_identity_scope}}的真实依据；各SKU与状态按下文区分。

B. 视觉风格参考图：{{look_reference_ids}}
仅锁定{{look_authority}}，不自动继承其中其他产品、品牌或具体构图。

C. 白模预演视频：{{previs_reference_ids}}
负责{{previs_authority}}；代理几何、中性材质和调试信息不进入最终画面。

D. 布局/其他输入：{{optional_reference_roles}}

## 视觉风格参考锁定

{{look_lock}}

## 产品身份与状态锁定

{{product_identity_lock}}

{{supported_product_states}}

{{product_material_and_structure_rules}}

## 包装文字身份锁定

{{packaging_text_and_layout}}

文字属于实际产品表面，保持原版式、位置与附着关系；随真实透视变化，不漂移、镜像、独立扶正或随机替换。不可辨认内容不补造。

## 文字可见度原则

{{text_visibility_windows}}

完整产品镜头优先保证包装布局正确，文字局部镜头优先保证真实字形和内容。运动与极端透视可使部分文字自然不可见，不能借此变成另一套文字；不为了同时看清全部字破坏摄影透视。

## 美术置景与布局结构锁定

{{art_direction_lock}}

{{layout_and_spatial_relationships}}

## 摄影系统

{{camera_system}}

{{motion_and_framing_rules}}

## 动态光影系统

{{lighting_system}}

{{lighting_constraints_and_material_response}}

## 料体与材料过程

{{material_process}}

## 白模预演使用规则

{{previs_use_rules}}

最终外观服从产品与影调参考；预演只提供已声明的相机、主体/置景运动与时序。{{unimplemented_appearance_instructions}}

## {{shot_id}} [{{shot_start_seconds}}—{{shot_end_seconds}}s]

{{shot_lens_and_sensor}}
{{shot_viewpoint_and_framing}}

{{shot_attention_and_entry_state}}

{{shot_camera_path_target_and_speed}}

{{shot_product_material_and_set_action}}

{{shot_light_shape_path_timing_and_response}}

{{shot_reading_window}}

{{shot_exit_cut_basis_and_next_entry}}

## 最终落版与停留

{{endcard_entry_and_completion}}

{{hold_start_seconds}}—{{duration_seconds}}秒：{{stable_hold_description}}
