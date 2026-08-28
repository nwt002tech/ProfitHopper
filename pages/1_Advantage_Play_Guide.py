import base64
import html
import json
import zlib

import streamlit as st

st.set_page_config(
    page_title="Coushatta AP Guide",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Compressed JSON keeps all 36 game cards self-contained while keeping this page lightweight.
_DATA = r"""c-o~~?Q+{na($I4Rb`c|Nl~OkeO7+Rwq*O3y;daox^{2fat(nYIaeTn#fKz%EBToR$Rp%Y@+f(dobH|h1|X&D-PCUFiXaHg^y!b&r^mniZ71J38xMA>owJ?WNEdpxGuT<-!-scw_^ZTUH(x$p;?D>CS^7H?d>HQ!%iN|aT1Sc5Q}41Q9?lEBGO^0D(pEN0OO>0Vv}L90w6clf`^Wp|%H3DySyifPX;L*aQMNMb(I)X8UZC-Ui+N=V{!OXI!^1O`WZAu%XN8))QVYCJ9#g6;RfRDL-F2|1!k<ltr@_w-UicZ_nc|&qGnHnQdeBL26x~~xvQDaUPu(qzvgy(kw!+H8=jb#RBQ*O~y1-VJx>74$VKwyhmCj+!Uw+vc|IdHpa=tSdAD<ljI{0O05?na^_1AwNFenoNh0F@`TrSpm^%67-zVDlH_YpvsI$H7$)l$RCkC`f~tia-<3@|hpVQct`uHmM-NP!0y&c7ox*m8hKrRJ&Pr{vnkVqcHcZB=CHLgn==v5_hx{5Z9^P}GSzQ+QfpG@M}ESpdv*_w}>N<{pKCny@Vi!>F<k;tlRwvS`V#5pxn)Z+OjFnygza4~J8}cU5Eak4E3)cJ*dyqI+c?OtDt5Qns?GroE45rXtVNbxBXx70`@ys$x5zKabk+aSyfQlLoZ|LG7(hBQn6-qF$9}%7MtA9Ecz7Vp*v_sIOTXn_?5s6}-;oiRJGSwlSNoy{_~ugN+!dvG^ypF|QNZiLxA7*h`rwdX1k>o`xq+!2<^D>RRC^$&iACRy@ld6AvqXaPV}d%6psdsYCq50GCUOa6D4a;PP|)5Eh<3y*g|0Q72E$C*b~IOH21U^m%!`fYW&n6ssi`O-`e#3>#b2i7r&fmI}_8VO#ynA8mTCDqAI{?7$XU-odqhJZa!M6u7=5RiV{QT`n0ab){D}S^IEH;m<K|;Lb$LG)uCDHKl{>_RZ%ncMh{8i|)TsU^vM5Ss!sx-Ey?>-#&RDmr`nIQsg;&Uv}ocfdS^oK1)-!5jhfQqYU{}9F%Z+O-3$pu{u*zm27*-qpg-MCl+R<ErlmA^*8g^li@-C7IGq;l$m<W3fvJTSxH&2%uPh`(*rR=o-yQ5v}{5uAtwi}Nv7ilcy;-tqe@-=j8M!?8gn9c>)?$Ig8D)Epug-8--~%+DPk|;2a_UunVrG$<dEX?lZ{i3u@4bnJmHILxLBkUb-m1xqMmjJM^nzhcNTsN4*+yW`v;AGOkEN#XdSQXI9_UTwULr*ZvYHk*htNxUl4NNHUj!uaL2MGhT9t)T-er$l-Ng`#@QqM$IPo?X=8(U8y!83I^iri(hxRQC$KsdF^W;|CLetrbiXlb2?KSWkfoe661+#&a5y~Lbem5ZC)oC9uhfbz$&LTo<biIaUjXFPsDmeYGX2e)>o^-_Y@e@bCGeCQa5eWh%F+6N8|eW?0C6%VSR0V&N*ne^0_z(MH@$+bkfN_`fwk_I>aIXmeJM$Y$d;9j?$_VA^fY;zE}@K+%MsVPa=n^mi8mmb7--rD8_UM1Xb~tH(XwK0k=CmjjEBO=20cgReRTDiT-~LGHYsf2n;KmJf6D9ff`M8YP3EKOz>8vnBjL3r>;bWN5f{2`5e^&-xuwutsXfM@Q~Jf@Q1}zSsS7rH7I3C?fkIp_mOdZIPlA*{@INjyT7zCAw{_6&!sRmi$@Hj!_&9+0tNpHv_)LA$3(%9h!e;*ue1othjE4g6h(kCpvIVdyB~ijcg-J9)igHHVX&nxsvBu7Tamy*2Xdy7K^aGGw8vS6~1S%-7MO~?Pk<h{J78dknUAUOaml>8ozA?)RY&Ef|Cp^6zPK8}4mFGpYaQ7G@38k9V<@#JGA$#h;VMor?26JNPygy&`T@-8~#4Rj><Kehv!6yRa>v}%dNv1B!$fPAIg9GrQ02EnNP=IewyGuhDd+=`9fRo`NN7ACm9#O2a6$&B#M4inZ;V9}@KDGOStAdFvunp;BXzx*00O}l`L%W?DP1T3m1yeP=_-J@6IkpWSwx%#mAY#)8)NZ@rx_F_EhqNMgCCA=2Nz|++QryX`ha>!le!+=>9#mpYiQ|UI5>xuJE^CfjA$<iHIf87qR<?qx&S^D-eFvE>W<NS<tK(@GoS+VF;PUD6?()Xr;(T^9p8SKb4Kwr>b$1UMM>4sl*r)sx6&ZqUgVCdtoVm|!i$e4WTqc2ESEKMJo!c4orePGE`TaoN8&Fsfp@-)6KgNTT{e2Y~n>cO~1d~nY#M4t^9pohBYK4htuaDfifFfZB#<iCoV*g6#14ts~L8n!aDjsxUeQDo7iwO$)6>3eU6W6Qo2c|kx_kmf`c;9`RHmHvG1y)Cq<Z&HF{EwmQpVtF+PhCsfh`MG9lSYUPIASEB0u&+>539m1h)_5)bA?00cye;$@qMYq6YDZ;T}&+pAwOrpUoedc%}jaCQX5Ydy(rcVnJLf-7x(Ngzv<{c2im3mjwHw=ha#OEfS!4Ajc*pIPWIFnmrl3wmp55DuOnNR>Q=+h<AXy+>zzqW0itkMW^{47PZ$5KrfmFXX=}d5{V1}2X)J17$<`kq9JN_=>=d5AEOmw=WYu4m^_lu}rry(k7sO^wRoQeGG-$C{qhO-Ke0WiBNHpyr^@;UviI@c^EUV$tRzsu}cLSIQ)u%o6noK#~|KI=oufzQT*fZ^5JjKT&e7vFdls=62_dTNTkvIu2$;pPq3=cnW1FY;k4N;Nzz|=%cb!xJ@q+~~q0+ZXucREr+S$RM|EYi%SXHNCfKjn5Yswh>G!-7Gr*r&vwX4udGHH0=Ir6QI^xUyKjr~<*@ePf@VP6@~c7P`_Bnz0jvZY&J((N<`6`2lD}&ltq7R2N3-lOb;bZ86mkN)6a#7sk8|TKdjm=duweXXbKTiG&D9<4QN9R4&n(8y^)yjAmvDB9k>8>-Bb}h~I;!sPV}wdS9b5z<P+ttN`zrO!+G<u^J&~o8mze2^}?k2UgyO>d%xCxC(RD#M<CB`W`+|JHT6sMB3|_K@cxW&)P~&!lcH7xw;@3V@F`5w7isV0!!*(>(M|I9=X0V1O*q5TUZZ#5uMRSKf%c~x{-`4)3siEz3AfItwZkT%bO2Ze|Ff-_-9+Vsrv#}0zIyCj-hH<5aSN_3~c4aErn}D%o$J(T$ga;&d>Li%{$-=j*hmCJCG$)Rvp#U#0wbzn#ky)(D^dp_}=n!dIPO&vzihal~+mvm0WusG#q|G9QEcYrzU|bye5HJn#)cX5t{jAdfK9L=-Y?9BK}7~XMP6??$EY02`sky#-P>gn1)g&p@?g{J2*6Im@qV=fhqh;!~a)#R%keKBZ;1eQlR|4i<Q$*o4evrP6hKQsaV1-UAG7pgfv=pdcA<GiU8!LpB5X^j?q$}+7|0z8z8kzwP@`?dQZ9h8XNFtj#jmqSG&?(-}d99gMg$sWrieR>hF;g-?V-EGm_mOpM&k2Z=<%uCpnDoiL=Ml>sW1%Y#U6uHw&6=M_PTm-4n63(5x^TxM`0x2&t)j+eJ}H%(ZFux?yq-+Cw2(d2%5@Zq-@2z0;z^P&hPHXa(*SG=0`}>FMyhDY8BF#}6q9Y{<Z)NLL8F1-vb-=cLaR_<4+rs$6C@JZ#2H)^TO98e6PP+~Ybu)W-YcwyhXDdFE}Q7l_W=9O=WTD~gkMG;rCVB^^9VzI_Xl@<p4XMh+CtkYQ>Jtlka-s8iw^Ao+iLLUiw@ggB@EoiA?9iOz*W*4ow<&cdx*c=eQ*)$iAJS=KAV?$OBXZWSoGMw!2o%*0zg59U*NL$%J$HfGW>I|-ygv2v=)RjuBFMSeszmH&DD`Sa}^$`)7}$=xHxdg^oSLbrltS?MQM{FosNOmonKfQOJ|2FJ?^X_eri5A-E>Yz0>{B&Dd57OTle8|$3uMK9fGP8XcjLcx(&;))Uo9J9{={__wYJXgmLL@Z+WJ6BwNobnI1*Ryuw0h3d>$pZv~(KT?=?M}gM^B_hwZ$~s4N*mo~ke}lKp$_kmI|sS!(80x^M{rWh=Lp$Lq_UR-Eu$MZ!;Fhehkb;x#aR-5FZG*y?MOExQ)V2NN*x${)wJ%eP&tkfu#Rm(*2%GITXyAa-fD_HM6{UMlZl~F4T9(#RK>We=oi7GMwzj6%-^x%;dI=Z`E<j~XP$$-cA@ZtM!#|5V%}$c;J*vhj{!c4Q-{xYEVy!Inss}2bIEgf3c1)C(8Y$E=T3v|1Qdw^QA_9rh9zA0c4ykq_Al}}T~`@JWF(?8PXeO^i47?rFcbNaL5WFXX6E6ZdNN38%+pEB>Ly;<D5z7v&a&i8U4cHKTakeKp^0AykDMO$ZARm(t>ht*c{e={_Tk$C<xs|)Cg}~l2pQi-wQE%{DxHxi!v@(CUwX0>+eKaIHWHdzBWfe(x$RLQj}Yv56$EpRMmlMz9(zC20@9?c1fFzq;1fePx8UYWa++vp_=WgKXMG*adMKQX1JImyac4Lx-MHqbngz~a?DzK~w<v79i5TN4a~ryWv{bLb$K>)^PNP+P!*Y=26t_h(s+Lp~@LfsKgq2q$s+%pGuc;jLP(P=wXC);-tNR4<#W?cg*A+4_jeo$v@yl6;*6&<k;J$e&ZX>O*bB+agRR@sJ+6bZ$52r(T)m}(^$%FGVb-6+|0_r3Bi#nc{)0yu9Hi1~dT<hTs?{5Vd-$il#D3?gPdbeciIisD!xoNUeF+JF&^=&M0Z`aStSmV)ARHHxQEZV-%w>&<6@J0Dj_`FECN#0+PiJ6(;b|PzDJWQNVbdD={8&bz}!bRI(6?@`pTTUiUK6qcx=ju=D8vl2uzM5T>-S-+l0!5#{Bm;HOkn>ENSn%~B%RQvktPoisQPCbaIY}dKXkX_rNo>mQ97v=h@v>fj>O6nse(26qiNlt@XO~jm;ahFWqB|vHy3XkNQzd@U1f=k7HrXH8WO8zZh+gAZ9auIDIzBjVmAQ!%3$DTVzQ|tA6kD66EmDGf7+m7bcFU+L*XwW249@%)DtMef-lPsxoYhP`kbf7P=Z;4+UC210ds2&qh0Zap4|B>6pt3amqg*h9?cjp${73jg83;>9v2M{E$kdrqNiX9)rw?>;6C>y3e~t%#Rz&>cx4Nu4V@FC$$c8x)LcFqD=Qk`o9v`$L{)rO^cyz^XdxeM8DXFE`s50QyHx{oMsh`XvEc;o*+kdEvgu{;2ayE5<U5VJ@1aKMedhOd!I5bJlXX=w#Xf>Jc4-cj+h4U1Ce}6ckkDv5!fN_j(aS0!7N+0p<cq$*QI-U;4lWCtGZx_I0V{%cEL<N^Mv`6F`&6G<P$pWr?@X)F9n)Vi=O!wBQrS1f8m#QxmpeIOhtco%ojM}<FT#E=*8`exaxSSpY@#ge_+e(A6e92kA`+Lr8y@23Q*2$TOb2Q9p=@eS!rl1{HI+w=K?+qrfpxmZaj>Cz*Od#ih^7it`0uRY)fG)VT8nqx8p16?rb7b=5URuIkD)hVE!xkLqnd=Hfw3i<Xzvy7{p-jjzz5F(jf#I#buj#B@bCqWnZ#gTe-cQDdN3E(eaoWKRoIl~AA|**AwvoEgU~wBnAw+3mR=zGZs$0<Z;OkLmAIc4noP}vo&7r4;ak(!o`HC(#NL<tS1S5v_h%1Z;PdM`r;SLw3KiU7MSAJyG2hI<m2H_c+c3A{o)X)c~43T>^{nnmx;YW<9;!c%WFtuuKB+hdVm_zB3bqU{EZO-;v92f>bc?6a>=zQUTnH){_TO3dP9O{8iVKQUiRK`0YW`cRJqi{5?@yXJ;pqIqzqF@4Oc<RpwDj2{GLpB7>Ps80o$u7<4leO^iqO7Lt{@`*^>jk<1_ZmmKV?Y)MmF>a}3iEbL{^*trfwxEAeVRS;#H-nudv8QXNj7Eho}EtuCf+-L@ge1|0lr`Tkn$ERycz%TxS9wpHjr|mM@O`ReVIpbMoZ(N?2ilANa|H+1c^a^y11iG$U@N;Cvt$)iJD<Y+i2x(QbJaWSYnGqVg2&w4IUn@Cph0m;ZvBu))p+rq}4O}X=ex6_N&XEw`k&Yke*HrrCSePbO1OyZFSQFCp=tX4Z;l7Wl`tV3kR9HZ4z<0Z<1=Bo78%(!6l@B4#v|IMe)D5QxI(h_QI7Q<-|oYBqb3(QtZ-;30ZsEG6R`?OC-6*m8qJzcRZpcIBMtEJU7eju|Xjne4F$_A*9ra@y2_IApxgEP=r$Q$QVI?dV21YGdwsrOXAgJ&bG+Q?%y|XQ{YzRW>j54Vhd8ohrvOACrj}0?hlnKXfn}%t<!s(?*4G!mD8`bXc2Y+ZjUtFOb=aQ(Vj%30|QAaf>U?+WeyjWLnBmP5HZ^|ifvj%AY?Z$cN(}8`a}a~S?C!tLQZoE9qgUvbV4>ij32~@2O3SO)bo&0$_%Mh{d(s=JBA)lgW>IgQz(9N=W=+^^n=p~wj3+pqOeBUBDLRPkBjSJq;olpK+R$+u8OwRG>%=B3vABBr5LdtY)}_SF6nu24+rT_{WzyV-&MpQ=H*c3wk-DpqX!K?SRi<Ig)Z{(s9o0WI+otBVh{sPeE3*L_v;lld-;$hHErrlT_AezDA3*|mj5-wNZs0mO4)V7Y3GNdqYH_r2UMnH5D5ks<BFY2@|trWAn>?^pi`Z!VKX$(Mrtx_`as9%wR2I%b*qN?42_@{7M=X-=*gg+(l&11lTn4dwaXq-NoAK<54wW5gkz-_W|P154U8V?nE6}Z%%>+Uc{^}Y#jXARJ)!en$GfFVTG!gC4=>1dFC?nQOa1JtXk&-S%_eNmShn-9Hu;Dlw|ICj{rm}?R{=K1dc@j$0AM8_YWmbBsjv+4pwZ&ZHudUfVtPv=^2Qra#;rDY;3SBzSu&@8TB0ta#OCGi*!U55cT4@Yj)zZSkvuXAd5hN@-f)p`&ZBkyJy<hd>l`BOSArx7dncmEE&cBC<UQs7`JZoPhQV9ubS`yI#!CXhzZ!ZUp2<2#a0W^d@k<t}{l80dfoW6hBTF`M*fjF#B*;`pU8?-n>J`mjE}ts$rhlL`^y>kw%saXF@U}*{_cRsIos^I>!d#X)*_3X6&5e0~t<4zNcM`u-MH=aaff%%Pq@AUA=RChtGek^nX6yas1=G3CKyNEk-mw3KPZ|9Be~`p_kp"""
GAMES = json.loads(zlib.decompress(base64.b85decode(_DATA)).decode("utf-8"))

STATUS = {
    "RULE": ("FIXED RULE", "#137A4B", "#E9F6EF"),
    "SCOUT": ("SCOUT STATE", "#205DA8", "#EAF2FC"),
    "METER": ("METER / COUNTER", "#205DA8", "#EAF2FC"),
    "VERIFY": ("PHOTO / VERIFY", "#A65C00", "#FFF3DE"),
}
ROUTE = {
    1: "Start here: clean public rule.",
    2: "Stored coins on reels 1–3.",
    3: "Stored multiplier is fast to spot.",
    4: "4–5 locked gold scatters + spins.",
    5: "High left multipliers + spins.",
    6: "Heavily loaded reels only.",
    7: "Photo borderline Cash Wizard states.",
    8: "6–7 row reels.",
    9: "Counter close to ceiling.",
    10: "Check every bet level.",
    11: "Lanterns near 40 / 60 / 100.",
    12: "Blue pig 18+.",
}

st.markdown(
    """
    <style>
      .block-container {padding-top:.7rem;max-width:760px}
      .hero {background:linear-gradient(135deg,#10243E,#173A5E);color:#fff;border-radius:18px;padding:17px;margin-bottom:10px}
      .ttl {font-size:1.45rem;font-weight:800}
      .sub {color:#d5dfeb;font-size:.88rem;margin-top:6px}
      .head {display:flex;gap:9px;align-items:flex-start;border:1px solid #D9E0E8;border-radius:15px;padding:12px;background:#fff}
      .num {background:#10243E;color:#fff;border-radius:12px;min-width:45px;height:45px;display:flex;align-items:center;justify-content:center;font-weight:800}
      .gt {font-weight:800;color:#10243E;line-height:1.15}
      .mk {color:#5B677A;font-size:.8rem;margin-top:3px}
      .bdg {margin-left:auto;border-radius:999px;padding:6px 8px;font-size:.67rem;font-weight:800;white-space:nowrap}
      .box {border:1px solid #D9E0E8;border-radius:13px;padding:11px;margin:8px 0;background:#fff}
      .lab {font-size:.7rem;font-weight:800;letter-spacing:.05em;color:#10243E;margin-bottom:5px}
      .warn {background:#FCEDED}
      .route {background:#FFF8EA;border:1px solid #E7D09F;border-radius:12px;padding:10px;margin:8px 0;color:#5c471c;font-size:.84rem}
      div[data-testid="stLinkButton"] a {background:#173A5E!important;color:#fff!important;border:none!important;border-radius:11px!important;min-height:42px;font-weight:700!important}
      div[data-testid="stButton"] button {min-height:42px;border-radius:11px}
    </style>
    """,
    unsafe_allow_html=True,
)


def state_svg(kind):
    if kind in ("scarab", "golden_egypt", "lock_spin", "sticky_reels", "frames", "grid", "prize_blocks"):
        cells = "".join(
            f'<rect x="{15+c*53}" y="{25+r*29}" width="45" height="22" rx="5" '
            f'fill="{"#FFF1B8" if (c+r)%3==0 else "#fff"}" stroke="#D8E2EC"/>'
            for r in range(3) for c in range(5)
        )
        label = "Persistent frames / coins / loaded positions"
    elif kind in ("counter", "meter", "progressive", "mhb5", "gems", "three_meters", "wolf_meters"):
        cells = "".join(
            f'<rect x="25" y="{30+i*30}" width="250" height="20" rx="7" fill="#fff" stroke="#D8E2EC"/>'
            f'<rect x="25" y="{30+i*30}" width="{width}" height="20" rx="7" fill="{color}" opacity=".25"/>'
            for i, (width, color) in enumerate([(225, "#205DA8"), (205, "#137A4B"), (185, "#A23B3B")])
        )
        label = "Read the actual meter / counter / ceiling"
    elif kind in ("multiplier", "reel_multiplier"):
        cells = (
            '<rect x="55" y="30" width="190" height="70" rx="14" fill="#fff" stroke="#D8E2EC"/>'
            '<text x="150" y="77" text-anchor="middle" font-size="38" font-weight="800" fill="#C7982E">5x</text>'
        )
        label = "Stored multiplier"
    elif kind == "reel_heights":
        cells = "".join(
            f'<rect x="{25+i*88}" y="{105-h}" width="60" height="{h}" rx="8" fill="#fff" stroke="#D8E2EC"/>'
            f'<text x="{55+i*88}" y="{110-h/2}" text-anchor="middle" font-size="13" font-weight="800" fill="#205DA8">{rows} rows</text>'
            for i, (h, rows) in enumerate([(50, 5), (76, 6), (100, 7)])
        )
        label = "Reels building toward 7 rows"
    elif kind == "lanterns":
        cells = (
            '<text x="30" y="45" font-size="15" font-weight="800" fill="#205DA8">BLUE 36 / 40</text>'
            '<text x="30" y="75" font-size="15" font-weight="800" fill="#137A4B">GREEN 55 / 60</text>'
            '<text x="30" y="105" font-size="15" font-weight="800" fill="#A23B3B">RED 92 / 100</text>'
        )
        label = "Lantern values — not the gold pig"
    elif kind in ("pigs", "piggy"):
        cells = "".join(
            f'<circle cx="{65+i*85}" cy="68" r="26" fill="{color}"/>'
            f'<text x="{65+i*85}" y="72" text-anchor="middle" font-size="10" font-weight="800" fill="#fff">{text}</text>'
            for i, (text, color) in enumerate([("BLUE 22", "#205DA8"), ("YELLOW", "#C7982E"), ("RED", "#A23B3B")])
        )
        label = "Persistent pig / bank state"
    elif kind in ("bubbles", "ocean", "spheres"):
        cells = "".join(
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="#EAF2FC" stroke="#205DA8" stroke-width="2"/>'
            for x, y, radius in [(55, 70, 21), (120, 48, 17), (190, 82, 25), (250, 52, 15)]
        )
        label = "Persistent object value + position"
    else:
        cells = (
            '<rect x="55" y="30" width="190" height="72" rx="14" fill="#fff" stroke="#D8E2EC"/>'
            '<text x="150" y="72" text-anchor="middle" font-size="24" font-weight="800" fill="#A65C00">PHOTO</text>'
        )
        label = "Capture full screen + meters + wager panel"

    return (
        '<div style="background:#EEF4F9;border-radius:14px;padding:7px;margin:8px 0">'
        '<svg viewBox="0 0 300 135" style="width:100%;height:auto">'
        '<text x="12" y="14" font-size="9" font-weight="700" fill="#62748A">ILLUSTRATED ADVANTAGE STATE</text>'
        + cells
        + f'<text x="150" y="128" text-anchor="middle" font-size="10" font-weight="700" fill="#10243E">{label}</text>'
        '</svg></div>'
    )


def render_game(game):
    label, color, bg = STATUS[game["s"]]
    st.markdown(
        f'<div class="head"><div class="num">#{game["p"]:02d}</div>'
        f'<div><div class="gt">{html.escape(game["t"])}</div><div class="mk">{html.escape(game["m"])}</div></div>'
        f'<div class="bdg" style="color:{color};background:{bg}">{label}</div></div>',
        unsafe_allow_html=True,
    )
    if game["p"] in ROUTE:
        st.markdown(f'<div class="route"><b>Tonight:</b> {ROUTE[game["p"]]}</div>', unsafe_allow_html=True)

    st.markdown(state_svg(game["v"]), unsafe_allow_html=True)
    st.markdown(
        f'<div class="box"><div class="lab">LOOK FOR</div>{html.escape(game["l"])}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="box" style="background:{bg};border-color:{color}55">'
        f'<div class="lab">ACTION RULE</div><b>{html.escape(game["a"])}</b></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="box warn"><div class="lab">DO NOT MISREAD</div>{html.escape(game["n"])}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Coushatta map")
    columns = st.columns(2)
    for i, (name, sid) in enumerate(game["maps"]):
        with columns[i % 2]:
            st.link_button(
                f"📍 {name} · SID {sid}",
                f"https://www.coushattacasinoresort.com/slot-map.php?sid={sid}",
                use_container_width=True,
            )

    favorites = st.session_state.setdefault("ap_favorites", set())
    is_favorite = game["p"] in favorites
    if st.button(
        "★ Remove favorite" if is_favorite else "☆ Add favorite",
        key=f'fav_{game["p"]}',
        use_container_width=True,
    ):
        if is_favorite:
            favorites.remove(game["p"])
        else:
            favorites.add(game["p"])
        st.rerun()


st.markdown(
    '<div class="hero"><div class="ttl">Coushatta Advantage-State Guide</div>'
    '<div class="sub">Native Streamlit page: reliable iPhone controls, quick game selector, favorites, '
    'illustrated state references and direct Coushatta map buttons.</div></div>',
    unsafe_allow_html=True,
)

view = st.radio(
    "View",
    ["Tonight’s Route", "All Games", "Favorites"],
    horizontal=True,
    label_visibility="collapsed",
)
query = st.text_input("Search", placeholder="Search Scarab, Buffalo, pig, meter…").lower().strip()
filter_name = st.selectbox(
    "Filter",
    ["All", "Fixed Rules", "Scout States", "Meters / Counters", "Photo / Verify"],
)
filter_status = {
    "All": None,
    "Fixed Rules": "RULE",
    "Scout States": "SCOUT",
    "Meters / Counters": "METER",
    "Photo / Verify": "VERIFY",
}[filter_name]

candidates = GAMES[:]
if view == "Tonight’s Route":
    candidates = [g for g in candidates if g["p"] <= 12]
elif view == "Favorites":
    favorites = st.session_state.setdefault("ap_favorites", set())
    candidates = [g for g in candidates if g["p"] in favorites]

if filter_status:
    candidates = [g for g in candidates if g["s"] == filter_status]

if query:
    candidates = [
        g for g in candidates
        if query in " ".join([g["t"], g["m"], g["l"], g["a"], g["n"]]).lower()
    ]

if view == "Tonight’s Route":
    with st.expander("Tonight’s scouting order", expanded=False):
        for priority in range(1, 13):
            game = next(g for g in GAMES if g["p"] == priority)
            st.markdown(f'**{priority}. {game["t"]}** — {ROUTE[priority]}')

if not candidates:
    st.warning("No games match the current view, filter, and search.")
    st.stop()

options = {f'{g["p"]:02d} · {g["t"]}': g for g in candidates}

pending = st.session_state.pop("ap_pending_game", None)
if pending is not None:
    for option, game in options.items():
        if game["p"] == pending:
            st.session_state["ap_selected_game"] = option
            break

if st.session_state.get("ap_selected_game") not in options:
    st.session_state["ap_selected_game"] = next(iter(options))

selected_option = st.selectbox(
    "Jump directly to a game",
    list(options),
    key="ap_selected_game",
)
selected = options[selected_option]

st.caption(
    f'{len(candidates)} matching game{"" if len(candidates) == 1 else "s"} — '
    'only the selected card is shown, so you do not have to scroll through the entire guide.'
)
render_game(selected)

with st.expander("Browse other matching games", expanded=False):
    for game in candidates:
        if game["p"] == selected["p"]:
            continue
        if st.button(
            f'{game["p"]:02d} · {game["t"]}',
            key=f'jump_{game["p"]}',
            use_container_width=True,
        ):
            st.session_state["ap_pending_game"] = game["p"]
            st.rerun()
