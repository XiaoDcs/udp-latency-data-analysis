import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
import os
import glob
import json
from pathlib import Path
import seaborn as sns
from scipy.spatial.distance import euclidean
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from math import radians, cos, sin, sqrt, atan2


class DroneCommAnalyzer:
    def __init__(self, data_folder):
        """
        初始化无人机通信数据分析器
        
        Args:
            data_folder (str): 测试数据文件夹路径
        """
        self.data_folder = data_folder
        self.sender_data = {}
        self.receiver_data = {}
        self.nexfi_data = {}
        self.gps_data = {}
        self.analysis_results = {}
        
        # 设置中国时区 (UTC+8)
        self.china_tz = timezone(timedelta(hours=8))
        
    def convert_to_china_time(self, timestamp_series):
        """将时间戳转换为中国时间"""
        return timestamp_series.dt.tz_localize('UTC').dt.tz_convert(self.china_tz)
        
    def load_data(self):
        """加载所有数据文件并进行数据清洗"""
        sender_folder = os.path.join(self.data_folder, 'sender')
        receiver_folder = os.path.join(self.data_folder, 'receiver')
        
        # 加载UDP发送方数据
        udp_sender_files = glob.glob(os.path.join(sender_folder, 'udp_sender_*.csv'))
        if udp_sender_files:
            self.sender_data['udp'] = pd.read_csv(udp_sender_files[0])
            self.sender_data['udp']['timestamp'] = pd.to_datetime(self.sender_data['udp']['timestamp'], unit='s')
            self.sender_data['udp']['timestamp'] = self.convert_to_china_time(self.sender_data['udp']['timestamp'])
            
        # 加载UDP接收方数据
        udp_receiver_files = glob.glob(os.path.join(receiver_folder, 'udp_receiver_*.csv'))
        if udp_receiver_files:
            self.receiver_data['udp'] = pd.read_csv(udp_receiver_files[0])
            self.receiver_data['udp']['send_timestamp'] = pd.to_datetime(self.receiver_data['udp']['send_timestamp'], unit='s')
            self.receiver_data['udp']['recv_timestamp'] = pd.to_datetime(self.receiver_data['udp']['recv_timestamp'], unit='s')
            self.receiver_data['udp']['send_timestamp'] = self.convert_to_china_time(self.receiver_data['udp']['send_timestamp'])
            self.receiver_data['udp']['recv_timestamp'] = self.convert_to_china_time(self.receiver_data['udp']['recv_timestamp'])
            
        # 加载NEXFI数据
        nexfi_sender_files = glob.glob(os.path.join(sender_folder, 'nexfi_status_*.csv'))
        nexfi_receiver_files = glob.glob(os.path.join(receiver_folder, 'nexfi_status_*.csv'))
        
        if nexfi_sender_files:
            self.nexfi_data['sender'] = pd.read_csv(nexfi_sender_files[0])
            self.nexfi_data['sender']['timestamp'] = pd.to_datetime(self.nexfi_data['sender']['timestamp'], unit='s')
            self.nexfi_data['sender']['timestamp'] = self.convert_to_china_time(self.nexfi_data['sender']['timestamp'])
            
        if nexfi_receiver_files:
            self.nexfi_data['receiver'] = pd.read_csv(nexfi_receiver_files[0])
            self.nexfi_data['receiver']['timestamp'] = pd.to_datetime(self.nexfi_data['receiver']['timestamp'], unit='s')
            self.nexfi_data['receiver']['timestamp'] = self.convert_to_china_time(self.nexfi_data['receiver']['timestamp'])
            
        # 加载GPS数据
        gps_sender_files = glob.glob(os.path.join(sender_folder, 'gps_logger_drone*_*.csv'))
        gps_receiver_files = glob.glob(os.path.join(receiver_folder, 'gps_logger_drone*_*.csv'))
        
        if gps_sender_files:
            self.gps_data['sender'] = pd.read_csv(gps_sender_files[0])
            self.gps_data['sender']['timestamp'] = pd.to_datetime(self.gps_data['sender']['timestamp'], unit='s')
            self.gps_data['sender']['timestamp'] = self.convert_to_china_time(self.gps_data['sender']['timestamp'])
            
        if gps_receiver_files:
            self.gps_data['receiver'] = pd.read_csv(gps_receiver_files[0])
            self.gps_data['receiver']['timestamp'] = pd.to_datetime(self.gps_data['receiver']['timestamp'], unit='s')
            self.gps_data['receiver']['timestamp'] = self.convert_to_china_time(self.gps_data['receiver']['timestamp'])
            
        # 数据清洗和时间范围对齐
        self._clean_and_align_data()
        
        print(f"数据加载完成:")
        print(f"  发送方UDP数据: {len(self.sender_data.get('udp', []))} 条记录")
        print(f"  接收方UDP数据: {len(self.receiver_data.get('udp', []))} 条记录")
        print(f"  发送方NEXFI数据: {len(self.nexfi_data.get('sender', []))} 条记录")
        print(f"  接收方NEXFI数据: {len(self.nexfi_data.get('receiver', []))} 条记录")
        print(f"  发送方GPS数据: {len(self.gps_data.get('sender', []))} 条记录")
        print(f"  接收方GPS数据: {len(self.gps_data.get('receiver', []))} 条记录")
        
        # 打印时间范围信息
        self._print_time_ranges()
        
    def _clean_and_align_data(self):
        """清洗和对齐数据，确保时间范围一致"""
        all_timestamps = []
        
        # 收集所有时间戳
        for data_type in ['udp']:
            if data_type in self.sender_data and not self.sender_data[data_type].empty:
                all_timestamps.extend(self.sender_data[data_type]['timestamp'].tolist())
            if data_type in self.receiver_data and not self.receiver_data[data_type].empty:
                if data_type == 'udp':
                    all_timestamps.extend(self.receiver_data[data_type]['recv_timestamp'].tolist())
                else:
                    all_timestamps.extend(self.receiver_data[data_type]['timestamp'].tolist())
        
        for role in ['sender', 'receiver']:
            if role in self.nexfi_data and not self.nexfi_data[role].empty:
                all_timestamps.extend(self.nexfi_data[role]['timestamp'].tolist())
            if role in self.gps_data and not self.gps_data[role].empty:
                all_timestamps.extend(self.gps_data[role]['timestamp'].tolist())
        
        if not all_timestamps:
            return
            
        # 确定总的时间范围
        min_time = min(all_timestamps)
        max_time = max(all_timestamps)
        
        print(f"数据时间范围: {min_time} 到 {max_time}")
        
        # 基于重叠时间过滤数据
        self._filter_data_by_time_range(min_time, max_time)
        
    def _filter_data_by_time_range(self, min_time, max_time):
        """根据指定的时间范围过滤数据"""
        # 过滤UDP数据
        if 'udp' in self.sender_data:
            mask = (self.sender_data['udp']['timestamp'] >= min_time) & (self.sender_data['udp']['timestamp'] <= max_time)
            self.sender_data['udp'] = self.sender_data['udp'][mask].copy()
            
        if 'udp' in self.receiver_data:
            mask = (self.receiver_data['udp']['recv_timestamp'] >= min_time) & (self.receiver_data['udp']['recv_timestamp'] <= max_time)
            self.receiver_data['udp'] = self.receiver_data['udp'][mask].copy()
            
        # 过滤NEXFI数据
        for role in ['sender', 'receiver']:
            if role in self.nexfi_data:
                mask = (self.nexfi_data[role]['timestamp'] >= min_time) & (self.nexfi_data[role]['timestamp'] <= max_time)
                self.nexfi_data[role] = self.nexfi_data[role][mask].copy()
                
        # 过滤GPS数据
        for role in ['sender', 'receiver']:
            if role in self.gps_data:
                mask = (self.gps_data[role]['timestamp'] >= min_time) & (self.gps_data[role]['timestamp'] <= max_time)
                self.gps_data[role] = self.gps_data[role][mask].copy()
                
    def _print_time_ranges(self):
        """打印各数据源的时间范围"""
        print("\n各数据源时间范围:")
        
        if 'udp' in self.sender_data and not self.sender_data['udp'].empty:
            start = self.sender_data['udp']['timestamp'].min()
            end = self.sender_data['udp']['timestamp'].max()
            print(f"  发送方UDP: {start} 到 {end}")
            
        if 'udp' in self.receiver_data and not self.receiver_data['udp'].empty:
            start = self.receiver_data['udp']['recv_timestamp'].min()
            end = self.receiver_data['udp']['recv_timestamp'].max()
            print(f"  接收方UDP: {start} 到 {end}")
            
        for role in ['sender', 'receiver']:
            if role in self.nexfi_data and not self.nexfi_data[role].empty:
                start = self.nexfi_data[role]['timestamp'].min()
                end = self.nexfi_data[role]['timestamp'].max()
                print(f"  {role} NEXFI: {start} 到 {end}")
                
            if role in self.gps_data and not self.gps_data[role].empty:
                start = self.gps_data[role]['timestamp'].min()
                end = self.gps_data[role]['timestamp'].max()
                print(f"  {role} GPS: {start} 到 {end}")
        
    def analyze_udp_performance(self):
        """分析UDP通信性能"""
        if 'udp' not in self.sender_data or 'udp' not in self.receiver_data:
            print("缺少UDP数据，跳过UDP性能分析")
            return
            
        sender_udp = self.sender_data['udp']
        receiver_udp = self.receiver_data['udp']
        
        # 计算基本统计
        total_sent = len(sender_udp)
        total_received = len(receiver_udp)
        packet_loss_rate = (total_sent - total_received) / total_sent * 100 if total_sent > 0 else 0
        
        # 延迟统计
        if not receiver_udp.empty and 'delay' in receiver_udp.columns:
            delay_stats = {
                'mean': receiver_udp['delay'].mean() * 1000,  # 转换为毫秒
                'median': receiver_udp['delay'].median() * 1000,
                'std': receiver_udp['delay'].std() * 1000,
                'min': receiver_udp['delay'].min() * 1000,
                'max': receiver_udp['delay'].max() * 1000,
                'p95': receiver_udp['delay'].quantile(0.95) * 1000,
                'p99': receiver_udp['delay'].quantile(0.99) * 1000
            }
        else:
            delay_stats = {
                'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0, 'p95': 0, 'p99': 0
            }
        
        # 计算吞吐量
        if not sender_udp.empty:
            test_duration = (sender_udp['timestamp'].max() - sender_udp['timestamp'].min()).total_seconds()
            if test_duration > 0 and 'packet_size' in sender_udp.columns:
                throughput_kbps = (total_received * sender_udp['packet_size'].iloc[0] * 8) / (test_duration * 1000)
            else:
                throughput_kbps = 0
        else:
            test_duration = 0
            throughput_kbps = 0
        
        self.analysis_results['udp'] = {
            'total_sent': total_sent,
            'total_received': total_received,
            'packet_loss_rate': packet_loss_rate,
            'delay_stats': delay_stats,
            'throughput_kbps': throughput_kbps,
            'test_duration': test_duration
        }
        
        print(f"\nUDP性能分析结果:")
        print(f"  总发包数: {total_sent}")
        print(f"  总收包数: {total_received}")
        print(f"  丢包率: {packet_loss_rate:.2f}%")
        print(f"  平均延迟: {delay_stats['mean']:.2f} ms")
        print(f"  最大延迟: {delay_stats['max']:.2f} ms")
        print(f"  延迟标准差: {delay_stats['std']:.2f} ms")
        print(f"  95%延迟: {delay_stats['p95']:.2f} ms")
        print(f"  吞吐量: {throughput_kbps:.2f} kbps")
        print(f"  测试持续时间: {test_duration:.1f} 秒")
        
    def analyze_nexfi_performance(self):
        """分析NEXFI通信质量"""
        nexfi_results = {}
        
        for role, data in self.nexfi_data.items():
            if data.empty:
                continue
                
            stats = {
                'rssi': {
                    'mean': data['avg_rssi'].mean(),
                    'std': data['avg_rssi'].std(),
                    'min': data['avg_rssi'].min(),
                    'max': data['avg_rssi'].max()
                },
                'snr': {
                    'mean': data['avg_snr'].mean(),
                    'std': data['avg_snr'].std(),
                    'min': data['avg_snr'].min(),
                    'max': data['avg_snr'].max()
                },
                'throughput': {
                    'mean': data['throughput'].mean(),
                    'std': data['throughput'].std(),
                    'min': data['throughput'].min(),
                    'max': data['throughput'].max()
                },
                'link_quality': {
                    'mean': data['link_quality'].mean(),
                    'std': data['link_quality'].std(),
                    'min': data['link_quality'].min(),
                    'max': data['link_quality'].max()
                }
            }
            nexfi_results[role] = stats
            
        self.analysis_results['nexfi'] = nexfi_results
        
        print(f"\nNEXFI通信质量分析结果:")
        for role, stats in nexfi_results.items():
            print(f"  {role}:")
            print(f"    平均RSSI: {stats['rssi']['mean']:.1f} dBm")
            print(f"    平均SNR: {stats['snr']['mean']:.1f} dB")
            print(f"    平均吞吐量: {stats['throughput']['mean']:.2f} Mbps")
            print(f"    平均链路质量: {stats['link_quality']['mean']:.1f}")
            
    def analyze_gps_trajectory(self):
        """分析GPS轨迹"""
        gps_results = {}
        
        for role, data in self.gps_data.items():
            if data.empty:
                continue
                
            # 计算3D距离
            distances = []
            if len(data) > 1:
                for i in range(1, len(data)):
                    dist = euclidean(
                        [data.iloc[i]['local_x'], data.iloc[i]['local_y'], data.iloc[i]['local_z']],
                        [data.iloc[i-1]['local_x'], data.iloc[i-1]['local_y'], data.iloc[i-1]['local_z']]
                    )
                    distances.append(dist)
                    
            # 计算速度
            speeds = []
            if len(data) > 1:
                for i in range(1, len(data)):
                    time_diff = (data.iloc[i]['timestamp'] - data.iloc[i-1]['timestamp']).total_seconds()
                    if time_diff > 0 and i-1 < len(distances):
                        speed = distances[i-1] / time_diff
                        speeds.append(speed)
                        
            # 计算航迹统计
            stats = {
                'total_distance': sum(distances) if distances else 0,
                'max_altitude': data['altitude'].max() if 'altitude' in data.columns else 0,
                'min_altitude': data['altitude'].min() if 'altitude' in data.columns else 0,
                'altitude_change': (data['altitude'].max() - data['altitude'].min()) if 'altitude' in data.columns else 0,
                'max_speed': max(speeds) if speeds else 0,
                'avg_speed': np.mean(speeds) if speeds else 0,
                'flight_time': (data['timestamp'].max() - data['timestamp'].min()).total_seconds(),
                'data_points': len(data)
            }
            
            gps_results[role] = stats
            
        self.analysis_results['gps'] = gps_results
        
        print(f"\nGPS轨迹分析结果:")
        for role, stats in gps_results.items():
            print(f"  {role}:")
            print(f"    数据点数: {stats['data_points']}")
            print(f"    总飞行距离: {stats['total_distance']:.2f} m")
            print(f"    高度变化: {stats['altitude_change']:.2f} m")
            print(f"    最大速度: {stats['max_speed']:.2f} m/s")
            print(f"    平均速度: {stats['avg_speed']:.2f} m/s")
            print(f"    飞行时间: {stats['flight_time']:.1f} s")
            
    def analyze_inter_drone_distance(self):
        """分析双机之间的3D距离"""
        if 'sender' not in self.gps_data or 'receiver' not in self.gps_data:
            print("GPS数据不完整，无法计算双机距离")
            return
            
        sender_gps = self.gps_data['sender']
        receiver_gps = self.gps_data['receiver']
        
        # 获取时间重叠部分
        start_time = max(sender_gps['timestamp'].min(), receiver_gps['timestamp'].min())
        end_time = min(sender_gps['timestamp'].max(), receiver_gps['timestamp'].max())
        
        # 过滤时间范围
        sender_gps_filtered = sender_gps[(sender_gps['timestamp'] >= start_time) & 
                                       (sender_gps['timestamp'] <= end_time)]
        receiver_gps_filtered = receiver_gps[(receiver_gps['timestamp'] >= start_time) & 
                                           (receiver_gps['timestamp'] <= end_time)]
        
        if sender_gps_filtered.empty or receiver_gps_filtered.empty:
            print("时间重叠部分无数据")
            return
            
        # 对齐时间戳
        distances_3d = []
        distances_horizontal = []
        distances_vertical = []
        timestamps = []
        
        for _, sender_row in sender_gps_filtered.iterrows():
            # 找最近的接收方数据点
            time_diffs = abs(receiver_gps_filtered['timestamp'] - sender_row['timestamp'])
            if time_diffs.empty:
                continue
                
            closest_idx = time_diffs.idxmin()
            
            # 如果时间差太大（超过1秒），跳过
            if time_diffs[closest_idx].total_seconds() > 1:
                continue
                
            receiver_row = receiver_gps_filtered.loc[closest_idx]
            
            # 使用经纬度计算距离
            # 将经纬度转换为米（使用简单的球面距离公式）
            # 地球半径（米）
            R = 6371000
            
            lat1 = radians(sender_row['latitude'])
            lon1 = radians(sender_row['longitude'])
            lat2 = radians(receiver_row['latitude'])
            lon2 = radians(receiver_row['longitude'])
            
            # 计算水平距离（使用Haversine公式）
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            horizontal_distance = R * c
            
            # 计算垂直距离（高度差）
            vertical_distance = abs(receiver_row['altitude'] - sender_row['altitude'])
            
            # 计算3D距离
            distance_3d = np.sqrt(horizontal_distance**2 + vertical_distance**2)
            
            distances_3d.append(distance_3d)
            distances_horizontal.append(horizontal_distance)
            distances_vertical.append(vertical_distance)
            timestamps.append(sender_row['timestamp'])
        
        if distances_3d:
            self.analysis_results['inter_drone_distance'] = {
                'timestamps': timestamps,
                'distances_3d': distances_3d,
                'distances_horizontal': distances_horizontal,
                'distances_vertical': distances_vertical,
                'mean_distance_3d': np.mean(distances_3d),
                'max_distance_3d': np.max(distances_3d),
                'min_distance_3d': np.min(distances_3d),
                'std_distance_3d': np.std(distances_3d),
                'mean_distance_horizontal': np.mean(distances_horizontal),
                'max_distance_horizontal': np.max(distances_horizontal),
                'min_distance_horizontal': np.min(distances_horizontal),
                'mean_distance_vertical': np.mean(distances_vertical),
                'max_distance_vertical': np.max(distances_vertical),
                'min_distance_vertical': np.min(distances_vertical)
            }
            
            print(f"\n双机3D距离分析结果:")
            print(f"  平均3D距离: {self.analysis_results['inter_drone_distance']['mean_distance_3d']:.2f} m")
            print(f"  最大3D距离: {self.analysis_results['inter_drone_distance']['max_distance_3d']:.2f} m")
            print(f"  最小3D距离: {self.analysis_results['inter_drone_distance']['min_distance_3d']:.2f} m")
            print(f"  3D距离标准差: {self.analysis_results['inter_drone_distance']['std_distance_3d']:.2f} m")
            print(f"  平均水平距离: {self.analysis_results['inter_drone_distance']['mean_distance_horizontal']:.2f} m")
            print(f"  平均垂直距离: {self.analysis_results['inter_drone_distance']['mean_distance_vertical']:.2f} m")
            
    def analyze_correlation(self):
        """分析通信质量与距离的相关性"""
        if 'inter_drone_distance' not in self.analysis_results:
            print("缺少距离数据，无法进行相关性分析")
            return
            
        # 获取距离数据
        distance_data = self.analysis_results['inter_drone_distance']
        distances = distance_data['distances_3d']
        timestamps = distance_data['timestamps']
        
        correlations = {}
        
        # 与UDP延迟的相关性
        if 'udp' in self.receiver_data and not self.receiver_data['udp'].empty:
            udp_data = self.receiver_data['udp']
            aligned_delays = []
            aligned_distances = []
            
            for _, udp_row in udp_data.iterrows():
                # 找到最接近的距离数据点
                time_diffs = [abs((ts - udp_row['recv_timestamp']).total_seconds()) for ts in timestamps]
                if not time_diffs:
                    continue
                closest_idx = time_diffs.index(min(time_diffs))
                
                if min(time_diffs) < 5:  # 5秒内的数据才考虑
                    aligned_delays.append(udp_row['delay'] * 1000)  # 转换为毫秒
                    aligned_distances.append(distances[closest_idx])
                    
            if len(aligned_delays) > 10:
                correlation, p_value = stats.pearsonr(aligned_distances, aligned_delays)
                correlations['delay_distance'] = {
                    'correlation': correlation,
                    'p_value': p_value,
                    'significant': p_value < 0.05,
                    'data_points': len(aligned_delays)
                }
                
        # 与NEXFI RSSI的相关性
        for role in ['sender', 'receiver']:
            if role in self.nexfi_data and not self.nexfi_data[role].empty:
                nexfi_data = self.nexfi_data[role]
                aligned_rssi = []
                aligned_distances = []
                
                for _, nexfi_row in nexfi_data.iterrows():
                    time_diffs = [abs((ts - nexfi_row['timestamp']).total_seconds()) for ts in timestamps]
                    if not time_diffs:
                        continue
                    closest_idx = time_diffs.index(min(time_diffs))
                    
                    if min(time_diffs) < 10:  # 10秒内的数据才考虑
                        aligned_rssi.append(nexfi_row['avg_rssi'])
                        aligned_distances.append(distances[closest_idx])
                        
                if len(aligned_rssi) > 5:
                    correlation, p_value = stats.pearsonr(aligned_distances, aligned_rssi)
                    correlations[f'rssi_distance_{role}'] = {
                        'correlation': correlation,
                        'p_value': p_value,
                        'significant': p_value < 0.05,
                        'data_points': len(aligned_rssi)
                    }
                    
        self.analysis_results['correlations'] = correlations
        
        print(f"\n相关性分析结果:")
        for key, corr in correlations.items():
            print(f"  {key}: r={corr['correlation']:.3f}, p={corr['p_value']:.3f} {'(显著)' if corr['significant'] else '(不显著)'} (n={corr['data_points']})")
            
    def run_full_analysis(self):
        """运行完整分析流程"""
        print("开始数据分析...")
        self.load_data()
        self.analyze_udp_performance()
        self.analyze_nexfi_performance()
        self.analyze_gps_trajectory()
        self.analyze_inter_drone_distance()
        self.analyze_correlation()
        print("\n数据分析完成!")
        
    def save_results(self, output_file):
        """保存分析结果到JSON文件"""
        # 处理datetime对象，转换为字符串
        results_copy = self.analysis_results.copy()
        
        if 'inter_drone_distance' in results_copy:
            timestamps = results_copy['inter_drone_distance']['timestamps']
            results_copy['inter_drone_distance']['timestamps'] = [ts.isoformat() for ts in timestamps]
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_copy, f, ensure_ascii=False, indent=2)
        print(f"分析结果已保存到: {output_file}")


def main():
    # 测试分析器
    data_folder = "20250612190350"
    if not os.path.exists(data_folder):
        print(f"数据文件夹 {data_folder} 不存在")
        return
        
    analyzer = DroneCommAnalyzer(data_folder)
    analyzer.run_full_analysis()
    
    # 保存结果
    output_file = f"analysis_results_{os.path.basename(data_folder)}.json"
    analyzer.save_results(output_file)


if __name__ == "__main__":
    main() 