# 计算模型与数据边界
版本v1.0。此规范用于统一教学基线，不是通用接收机完整算法规范。建议先用公开卫星检查点验证轨道与钟差，再进行整段定位。

## 1. 范围与常数
GPS单系统、L1 C1伪距、广播星历、单历元四未知数 `[x,y,z,b]`，`b=c·dt_receiver`为米。无载波相位、RTK/PPP、多系统时间偏差、IMU、海拔约束或地图匹配。允许用上一解作为数值初值，不允许用其作为固定坐标/高度约束绕过可解条件。

| 常数 | 数值 |
|---|---|
| c | 299792458 m/s |
| mu_GPS | 3.986005e14 m³/s² |
| omega_E | 7.2921151467e-5 rad/s |
| F（周期相对论） | -4.442807633e-10 s/√m |
| WGS84 a | 6378137 m |
| WGS84 f | 1/298.257223563 |

广播星历角度及角速率使用rad及rad/s，不要再次乘π；Klobuchar公式中的部分量使用半圆，须明确转换。此数据GPS周为1316，星历toe/toc周内秒与GPS周配套，使用时间范围短于2小时。超出配套时间不能继续外推并宣称有效。系统不处理跨GPS周、星历切换、多信号偏差与闰秒更新等完整产品问题。

## 2. 广播星历计算 [1]
A=sqrt_a²；tk=t_tx-toe（归化至±302400秒）；n=sqrt(mu/A³)+delta_n；M=m0+n·tk。迭代解 `E-e sin(E)=M`。

v=atan2(sqrt(1-e²)sinE,cosE-e)，phi=v+omega。

u=phi+cus·sin(2phi)+cuc·cos(2phi)

r=A(1-e cosE)+crs·sin(2phi)+crc·cos(2phi)

i=i0+idot·tk+cis·sin(2phi)+cic·cos(2phi)

Omega=omega0+(omega_dot-omega_E)·tk-omega_E·toe

令xp=r cosu，yp=r sinu，则发射时刻ECEF为：

X=xp cosOmega-yp cosi sinOmega；Y=xp sinOmega+yp cosi cosOmega；Z=yp sini。

卫星系统钟差 `dt_sat=af0+af1·tc+af2·tc²+F·e·sqrt_a·sinE`，tc=t_tx-toc归化至半周。该定义**含周期相对论项，不含TGD**。`satellite_checkpoints.csv`中的卫星坐标也尚未旋转至接收时刻坐标架。

## 3. C1观测、发射时刻与地球自转 [2]
本作业采用：

`P = rho + b - c·dt_sat + c·TGD + I + T + epsilon + fault`

等价定义 `dt_code=dt_sat-TGD`。不能减了TGD又在伪距端重复改正。

输入t_rx为以GPS周/周内秒表示的接收机时标；待估b反映其相对GPST的偏差。配套仿真也遵循该定义。初始t_tx=t_rx-P/c，再迭代 `t_tx=t_rx-P/c-dt_code(t_tx)`；真实接收GPST约为t_rx-b/c。

信号传播时间 `tau=(P+c·dt_code-b)/c`。将发射时刻卫星位置s按下式旋转至接收时刻ECEF，再计算几何距离；不要重复加入另一个Sagnac距离项：

```
w = omega_E * tau
s_rx.x =  cos(w)*s.x + sin(w)*s.y
s_rx.y = -sin(w)*s.x + cos(w)*s.y
s_rx.z =  s.z
rho = norm(s_rx - receiver_xyz)
```

观测噪声和人工偏差也会通过发射时刻近似引入极小差异，因此全星共同+100m时位置应近似不变，不要求浮点位完全相同。

## 4. 大气改正
电离层采用Klobuchar [3]，导航文件中的参数：

alpha=[1.1180e-8,1.4900e-8,-5.9600e-8,-5.9600e-8]

beta=[8.8060e4,1.6380e4,-1.9660e5,-1.3110e5]

令φu=纬度/π、λu=经度/π、E=高度角/π（半圆），A为方位角（rad）。ψ=0.0137/(E+0.11)-0.022；φi=clip(φu+ψcosA,-0.416,0.416)；λi=λu+ψsinA/cos(πφi)；φm=φi+0.064cos[π(λi-1.617)]。

当地秒t=(43200λi+GPST周内秒) mod 86400；AMP=max(0,Σalpha_j·φm^j)；PER=max(72000,Σbeta_j·φm^j)；x=2π(t-50400)/PER；映射因子F_i=1+16(0.53-E)³。

|x|<1.57时，I=c·F_i·[5e-9+AMP(1-x²/2+x⁴/24)]；否则I=c·F_i·5e-9。模型评价时GPST可使用t_rx-b/c。

对流层采用固定标准气象的Saastamoinen教学版本。明确采用下列常数，避免不同实现造成基线差异。纬度lat为rad，椭球高h为m，高度角el为rad；取h=max(0,h)，相对湿度0.7：

```
p = 1013.25*(1-2.2557e-5*h)**5.2568          # hPa
temp = 15-6.5e-3*h+273.16                  # K
e_vap = 6.108*0.7*exp((17.15*temp-4684)/(temp-38.45))
T_dry = .0022768*p/(1-.00266*cos(2*lat)-.00028*h/1000)/sin(el)
T_wet = .002277*(1255/temp+.05)*e_vap/sin(el)
T = T_dry + T_wet                         # m
```

这是固定气象近似，不是实测气象真值或精密映射函数。地心初值无法给出合理高度时，先不施加大气改正，获得近地表粗解后再启用并迭代。异常高度/el≤0时不得让公式产生非有限值。教学数据有效卫星高度角均高于3°；为一致性，基础版使用3°统一截止高度角，不能默认10°导致4星测试额外丢星。

## 5. 定位与诊断
使用至少4条独立观测估计XYZ和b，线性化几何行约为 `[(x-xs)/rho,(y-ys)/rho,(z-zs)/rho,1]`。建议用QR/SVD/最小二乘库解线性系统；迭代重新计算高度角、大气与残差，报告收敛失败。基础结果采用普通等权最小二乘，不增加时序约束。

改进版方法由学生设计，可采用加权、鲁棒估计、基于残差的一致性检验等，但须解释检测与处置依据并做消融比较。验收强故障以单星故障为主；多个相关偏差的唯一识别、航空级保护水平、欺骗信号辨识不在必做范围。低残差与低DOP均不能证明真实误差小 [4]。

PDOP按参与定位卫星的未加权几何矩阵H计算：Q=(HᵀH)^-1，PDOP=sqrt(Qxx+Qyy+Qzz)；秩不足则无有效PDOP。不允许用权重调小PDOP冒充几何改善。4星虽可能解算，但没有单历元观测冗余；3星不能完成本题的独立四未知数解算。

## 6. 数据层级与可作出的结论
D01：真实历史C1摘录，20历元、160条观测，约30秒间隔，最后时刻有0.001秒小数。未添加人工异常。原文件头仅为近似坐标，不提供独立测量真值；不能据此宣称绝对精度或给逐星异常贴真值标签。C/N0在源文件缺失，输入保持null。

D02/D03及教师测试：使用真实广播轨道/钟差，但接收机轨迹、钟差、C/N0、伪距噪声和故障为仿真。基础伪距噪声标准差0.8m，叠加幅度0.25m的平滑小扰动；并非对自然城市多路径的完整复现。位置、钟差与注入标签为精确的**仿真真值**。不能把其中米级结果宣传成手机或城市道路实测精度。

D03公开事件（闭区间，epoch_id）：120—179为G19+80m；300—359全星+100m；420—439为4星；460—479为3星；520—529为0星；其余为正常动态/停止。所有变化作用在数据中，不是射频干扰。

参考轨迹只用于评价，禁止作为定位输入。公开开发答案不代表未知验收案例的答案。

## 7. 来源
[1] ESA Navipedia, GPS and Galileo Satellite Coordinates Computation:
https://gssc.esa.int/navipedia/index.php/GPS_and_Galileo_Satellite_Coordinates_Computation

[2] ESA Navipedia, Emission Time Computation:
https://gssc.esa.int/navipedia/index.php/Emission_Time_Computation

[3] ESA Navipedia, Klobuchar Ionospheric Model:
https://gssc.esa.int/navipedia/index.php/Klobuchar_Ionospheric_Model

[4] ESA Navipedia, Positioning Error:
https://gssc.esa.int/navipedia/index.php/Positioning_Error

[5] Real observations/navigation: RTKLIB test/data/rinex/07590920.05o and 07590920.05n; original agency GSI, JAPAN. Exact extraction ranges, source Git blob IDs and approximate-header warning: data/provenance.json. See LICENSE_RTKLIB.txt. This is a teaching extract, not an untouched complete original RINEX observation file.
