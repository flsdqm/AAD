import traceback
import streamlit as st
import pandas as pd
import base64
import datetime
import mysql.connector
import joblib
from joblib import load
import numpy as np
import os
from io import BytesIO

# 连接数据库
def connect_to_database():
    try:
        conn = mysql.connector.connect(
            host='121.199.62.25',
            database='aad',
            user='aad',
            password='zCzE5862HFRDMPcS'
        )
        st.write("🌞 数据库连接成功，数据可写入数据库")
        return conn
    except mysql.connector.Error as e:
        st.write(f"💥 数据库连接失败: {e}")
        return None


# 获取当前脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 构建相对路径
# model_path = os.path.join(script_dir, '..', 'models', 'LR_8rwd2_0425.pkl')
model_path = os.path.join(script_dir, 'models', 'LR_8rwd2_0425.pkl')

# 加载模型
try:
    rf = load(model_path)
    st.success("模型加载成功！")
except FileNotFoundError:
    st.error(f"错误：模型文件未找到 - {model_path}")

st.title('''主动脉夹层(AAD)风险预测''')

# 生成 Excel 下载按钮（单工作表版本）
def download_excel_button(df, file_name):
    """使用 Streamlit 原生按钮下载 Excel 文件（单工作表）"""
    try:
        # 创建内存中的二进制流
        output = BytesIO()
        
        # 直接写入单个工作表
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='预测数据', index=False)
        
        # 重置流位置并生成下载按钮
        output.seek(0)
        st.download_button(
            label="📥 下载 Excel 文件",
            data=output,
            file_name=f"{file_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="点击此处下载预测数据为 Excel 格式"
        )
        return True
    except Exception as e:
        st.error(f"生成 Excel 文件时出错: {e}")
        return False

# 用户身份验证
def authenticate():
    st.subheader('请输入密码')
    password = st.text_input("", type="password",  placeholder="请输入密码")
    if password == "123456":
        return True
    else:
        st.warning("密码错误，请重新输入。")
        return False


# 主程序
def main():
    # 身份验证
    authenticated = authenticate()
    if not authenticated:
        return

    # 输入患者信息
    st.header("输入患者基本信息")
    patient_sn = st.text_input("输入患者SN", "00001")
    name = st.text_input("输入患者姓名", "张三")
    gender = st.selectbox("选择患者性别", ["男性", "女性"])
    age = st.number_input("输入患者年龄", min_value=0, max_value=150, step=1)

    # 输入预测指标
    st.header("输入预测指标")
    sudden_onset = st.selectbox("是否突发", ["是", "否"])
    chest_pain = st.selectbox("胸痛", ["有", "无"])
    sweating = st.selectbox("大汗", ["有", "无"])
    shortness_of_breath = st.selectbox("呼吸困难", ["有", "无"])
    hypertension_history = st.selectbox("高血压病史", ["有", "无"])
    systolic_bp = st.number_input("输入收缩压 (mmHg)", min_value=0, max_value=500, step=1, value=0)
    diastolic_bp = st.number_input("输入舒张压 (mmHg)", min_value=0, max_value=500, step=1, value=0)
    rbc = st.number_input("输入红细胞计数 (×10^12/L)", min_value=0.00, max_value=100.0, step=0.1, value=0.00)
    wbc = st.number_input("输入白细胞计数 (×10^9/L)", min_value=0.00, max_value=100.0, step=0.1, value=0.00)
    urea = st.number_input("输入尿素 (mmol/L)", min_value=0.00, max_value=100.0, step=0.1, value=0.00)
    creatinine = st.number_input("输入肌酐 (μmol/L)", min_value=0, max_value=1000, step=1, value=0)
    d_dimer = st.number_input("输入D-D二聚体定量 (mg/L)", min_value=0.00, max_value=100.0, step=0.1, value=0.00)

    # 输入实际结果
    st.header("是否患急性主动脉夹层")
    illness = st.selectbox("是否患病", ["是", "否"])

    # 预测按钮
    st.header("开始预测风险")
    if st.button("开始预测"):
        inputs = {
            "patient_sn": patient_sn,
            "name": name,
            "gender": gender,
            "age": age,
            "sudden_onset": sudden_onset,
            "chest_pain": chest_pain,
            "sweating": sweating,
            "shortness_of_breath": shortness_of_breath,
            "hypertension_history": hypertension_history,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "rbc": rbc,
            "wbc": wbc,
            "urea": urea,
            "creatinine": creatinine,
            "d_dimer": d_dimer,
        }

        # 将输入值转换为数值（0 或 1）
        input_data = {
            "性别": 1 if gender == "男性" else 0,
            "年龄": age,
            "是否突发": 1 if sudden_onset == "是" else 0,
            "胸痛": 1 if chest_pain == "有" else 0,
            "大汗": 1 if sweating == "有" else 0,
            "呼吸困难": 1 if shortness_of_breath == "有" else 0,
            "高血压病史": 1 if hypertension_history == "有" else 0,
            "收缩压": systolic_bp,
            "舒张压": diastolic_bp,
            "红细胞计数": rbc,
            "白细胞计数": wbc,
            "尿素": urea,
            "肌酐": creatinine,
            "D-D二聚体定量": d_dimer
        }

        # 在生成 input_data 后，检查并过滤特征
        model_expected_features = [
            "性别", "年龄", "是否突发", "胸痛", "大汗", "呼吸困难",
            "高血压病史", "收缩压", "舒张压", "尿素", "肌酐", "D-D二聚体定量"
        ]

        # 过滤输入数据，仅保留模型需要的特征
        input_data_filtered = {k: v for k, v in input_data.items() if k in model_expected_features}

        # 转换为 DataFrame 时指定顺序
        input_df = pd.DataFrame([input_data_filtered], columns=model_expected_features)

        # # 打印检查信息
        # st.write("输入数据维度:", input_df.shape)
        # st.write("输入数据特征:", input_df.columns.tolist())

        # 将输入数据转为适合模型的 DataFrame 格式
        # input_df = pd.DataFrame([input_data])

        # 使用训练好的模型进行预测
        prediction_rf = rf.predict(input_df)

        # 根据模型预测结果输出预测
        prediction = prediction_rf[0]  # 获取单个预测结果

        # 输出预测结果
        risk = prediction
        st.success(f"预测结果为：{risk}")

        # 构建插入语句
        sql ="""
                INSERT INTO patient_features
                (patient_id, name, gender, age, sudden_onset, chest_pain, sweating, 
                 shortness_of_breath, hypertension_history, systolic_bp, diastolic_bp, 
                 rbc, wbc, urea, creatinine, d_dimer, risk, illness)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

        # 保存数据至数据库
        conn = connect_to_database()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, (
                    inputs["patient_sn"],
                    inputs["name"],
                    1 if inputs["gender"] == "男性" else 0,
                    inputs["age"],
                    1 if inputs["sudden_onset"] == "是" else 0,
                    1 if inputs["chest_pain"] == "有" else 0,
                    1 if inputs["sweating"] == "有" else 0,
                    1 if inputs["shortness_of_breath"] == "有" else 0,
                    1 if inputs["hypertension_history"] == "有" else 0,
                    inputs["systolic_bp"],
                    inputs["diastolic_bp"],
                    inputs["rbc"],
                    inputs["wbc"],
                    inputs["urea"],
                    inputs["creatinine"],
                    inputs["d_dimer"],
                    risk,
                    illness
                ))
                conn.commit()
                st.write("数据成功写入数据库")

                # 查询并展示数据
                query = "SELECT * FROM patient_features ORDER BY create_time DESC"
                cursor.execute(query)
                result = cursor.fetchall()
                df = pd.DataFrame(result, columns=[
                    "patient_id", "name", "gender", "age", "sudden_onset", "chest_pain",
                    "sweating", "shortness_of_breath", "hypertension_history",
                    "systolic_bp", "diastolic_bp", "rbc", "wbc", "urea",
                    "creatinine", "d_dimer", "risk", "illness", "create_time"
                ])

                # 将英文列名转换为中文列名
                df.columns = [
                    "患者SN", "姓名", "性别", "年龄", "是否突发", "胸痛", "大汗",
                    "呼吸困难", "高血压病史", "收缩压", "舒张压",
                    "红细胞计数", "白细胞计数", "尿素", "肌酐", "D-D二聚体定量",
                    "预测风险", "是否患病", "创建时间"
                ]

                st.write("以下是保存的数据:")
                st.dataframe(df)

                # 获取当前时间作为文件名
                current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                file_name = f"主动脉夹层风险预测_{current_time}"

                # 下载数据（优化版）
                download_excel_button(df, file_name)

            except mysql.connector.Error as e:
                # 捕获 MySQL 特定的错误，并提供详细的错误信息
                st.write("💥 写入数据库时发生错误:")
                st.write(f"错误代码: {e.errno}")  # 错误代码
                st.write(f"错误消息: {e.msg}")  # 错误消息
                st.write(f"错误 SQL 状态: {e.sqlstate}")  # 错误的 SQL 状态码
                st.write(f"详细错误信息: {traceback.format_exc()}")  # 打印详细堆栈信息

            except Exception as e:
                # 捕获其他一般性异常并提供详细信息
                st.write("💥 数据库连接失败或其他错误发生:")
                st.write(f"错误类型: {type(e).__name__}")  # 异常类型
                st.write(f"错误消息: {str(e)}")  # 异常消息
                st.write(f"详细错误信息: {traceback.format_exc()}")  # 打印详细堆栈信息

            finally:
                cursor.close()
                conn.close()


# 主程序入口
if __name__ == "__main__":
    main()
