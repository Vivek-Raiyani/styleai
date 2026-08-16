import re
import html
import json
from db import SessionLocal, Asset, init_db

raw_html = """<div class="option-modal__grid"><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                
    # full body
    ring-brand-1000 ring-3"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_01_8190f45a28.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_02_e8b9d78f2e.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_03_e005cc9acb.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_04_5c8ecc3df0.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_05_6364e97f94.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_06_ec697568e1.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_07_a2ac0b93ad.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_08_9f31d68329.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_09_e7651cae37.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_10_48704b9df2.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-11" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_11_98ce881608.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-12" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_12_ce6b132d80.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-13" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_13_c8c9f79e6d.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-14" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_14_cd720380cc.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-15" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_15_8dec5bad7a.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-16" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_16_8dd8b721f0.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-17" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_17_49ffb2a8a0.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-18" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_18_0642209a4f.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-19" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_19_613e13a00d.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-20" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_20_d38d8dc4eb.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-21" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_21_453ae368d5.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-22" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_22_a00378ed61.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-23" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_23_4d21665b9e.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-24" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_24_a2e77d6cb8.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-25" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_25_742b310ad2.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-26" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_26_3b6cb3fa7e.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-27" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_27_d2c3010327.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-28" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_28_e18605bd43.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-29" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_29_153b8644d8.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-30" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_30_69c4bb8d88.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-31" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_31_5d0d21c71e.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-32" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_32_7374a3091d.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-33" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_33_4e08d9218c.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-34" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_34_56d1792a86.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-35" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_35_fc5fa4f1f4.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-36" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_36_08912fb5e2.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-37" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_37_c13b242971.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-38" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_38_f3ed50e52f.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-39" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_39_b4544b575a.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="full-40" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_full_body_40_d716f5f2a7.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                
                # upper body
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_01_3f376bb653.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_02_f9c20f7e80.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_03_cc0c9bf1db.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_04_64349d9760.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_05_e905b83463.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_06_787acd17ec.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_07_3aeec0bfe1.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_08_9d61de1dca.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_09_35850fad6c.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="upper-10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_upper_body_10_bac2b8bf8a.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                
                # lower body
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_01_6a2df013ca.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_02_f3cbaace57.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_03_cdd60e1ac5.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_04_cbbaf1e819.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_05_818b5ffd33.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_06_d978e1e4a6.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_07_5fb47ca5e9.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_08_fc19f59031.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_09_4b033d11d0.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="lower-10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_clothes_reference_lower_body_10_4de90f9e50.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                
                #outer
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_02_f08cb507ce.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_016_364e8d57e5.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_017_3a7edfc3cc.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_024_6e5385d975.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_03_36e0f671a8.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_01_54a065a6c0.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_025_3dc8212248.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_013_03cc287218.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_022_575c843a5c.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_012_3eb7bd17cc.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-11" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_07_e005c701b4.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-12" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_09_61a0d70ea1.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="outer-13" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_webp_outerwear_010_a7af0d06cc.png"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                
                # shoes

                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-1" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_1_b2f3397ee0.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-2" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_2_ec3578c5c2.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-3" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_3_428e8dddb1.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-4" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_4_c30f27f548.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-5" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_5_c3520502dc.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-6" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_6_a8a634f576.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-7" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_7_feae35a15c.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-8" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_8_343dceaf61.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-9" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_9_52a61e0935.jpg"></div></div><div class="relative cursor-pointer overflow-hidden rounded-lg bg-white p-0.5 transition-all
                hover:ring-brand-200 hover:ring-2"><div class="aspect-[3/4] overflow-hidden rounded-lg"><img alt="shoes-10" class="h-full w-full object-cover" src="https://plugins-media.makeupar.com/strapi/assets/small_Shoes_10_d67d107868.jpg"></div></div></div>"""

def parse_items(text):
    pattern = re.compile(r'<img[^>]+alt="([^"]+)"[^>]+src="([^"]+)"', re.IGNORECASE)
    matches = pattern.findall(text)
    items = []
    for alt, src in matches:
        alt_clean = html.unescape(alt).strip()
        url = src.strip()
        
        # Determine category and human name
        if alt_clean.startswith("full-"):
            num = alt_clean.replace("full-", "")
            items.append({
                "category": "garment",
                "subcategory": "full_body",
                "name": f"Full Body Look #{num}",
                "tag": alt_clean,
                "url": url
            })
        elif alt_clean.startswith("upper-"):
            num = alt_clean.replace("upper-", "")
            items.append({
                "category": "garment",
                "subcategory": "upper_body",
                "name": f"Top / Upper Wear #{num}",
                "tag": alt_clean,
                "url": url
            })
        elif alt_clean.startswith("lower-"):
            num = alt_clean.replace("lower-", "")
            items.append({
                "category": "garment",
                "subcategory": "lower_body",
                "name": f"Bottom / Lower Wear #{num}",
                "tag": alt_clean,
                "url": url
            })
        elif alt_clean.startswith("outer-"):
            num = alt_clean.replace("outer-", "")
            items.append({
                "category": "garment",
                "subcategory": "outerwear",
                "name": f"Outerwear / Coat #{num}",
                "tag": alt_clean,
                "url": url
            })
        elif alt_clean.startswith("shoes-"):
            num = alt_clean.replace("shoes-", "")
            items.append({
                "category": "shoes",
                "subcategory": "shoes",
                "name": f"Footwear Pair #{num}",
                "tag": alt_clean,
                "url": url
            })
    return items

items = parse_items(raw_html)
print(f"Total items parsed: {len(items)}")

# Count by category & subcategory
from collections import Counter
counts = Counter((i["category"], i["subcategory"]) for i in items)
for k, v in counts.items():
    print(f"  {k[0]} ({k[1]}): {v}")

# Save to JSON
with open("clothes_shoes_data.json", "w", encoding="utf-8") as f:
    json.dump(items, f, indent=2, ensure_ascii=False)

print("Saved items to clothes_shoes_data.json")

# Sync to DB
init_db()
db = SessionLocal()
try:
    inserted = 0
    updated = 0

    for item in items:
        url = item["url"]
        name = item["name"]
        cat = item["category"]
        subcat = item["subcategory"]
        tag = item["tag"]
        key = f"cdn_{cat}_{tag.replace('-', '_')}"
        meta = json.dumps({"subcategory": subcat, "tag": tag})

        existing = db.query(Asset).filter(
            Asset.category == cat,
            (Asset.b2_url == url) | (Asset.b2_key == key)
        ).first()

        if existing:
            existing.name = name
            existing.b2_url = url
            existing.thumbnail_url = url
            existing.meta_json = meta
            updated += 1
        else:
            new_asset = Asset(
                category=cat,
                name=name,
                b2_key=key,
                b2_url=url,
                thumbnail_url=url,
                meta_json=meta
            )
            db.add(new_asset)
            inserted += 1

    db.commit()
    print(f"Database sync: {inserted} inserted, {updated} updated.")
    garments_count = db.query(Asset).filter(Asset.category == "garment").count()
    shoes_count = db.query(Asset).filter(Asset.category == "shoes").count()
    print(f"Total garments in DB: {garments_count}, Total shoes in DB: {shoes_count}")
finally:
    db.close()
