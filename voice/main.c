#include "stm32f4xx.h"
#include <stdio.h>

// 串口协议状态机状态枚举
typedef enum {
    REV_STATE_HEAD0   = 0x00,
    REV_STATE_HEAD1   = 0x01,
    REV_STATE_LENGTH0 = 0x02,
    REV_STATE_LENGTH1 = 0x03,
    REV_STATE_TYPE    = 0x04,
    REV_STATE_CMD     = 0x05,
    REV_STATE_SEQ     = 0x06,
    REV_STATE_DATA    = 0x07,
    REV_STATE_CKSUM0  = 0x08,
    REV_STATE_CKSUM1  = 0x09,
    REV_STATE_TAIL    = 0x0a,
} eRecvState_t;

#define DF2301Q_UART_MSG_HEAD_LOW    0xF4
#define DF2301Q_UART_MSG_HEAD_HIGH   0xF5
#define DF2301Q_UART_MSG_TAIL        0xFB
#define DF2301Q_UART_MSG_DATA_MAX_SIZE 8

// 状态机相关变量
static volatile eRecvState_t recvState = REV_STATE_HEAD0;
static volatile uint16_t length = 0;
static volatile uint16_t dataCount = 0;
static volatile uint8_t packetData[DF2301Q_UART_MSG_DATA_MAX_SIZE];
static volatile uint8_t uartCmdId = 0;
static volatile uint16_t checksum = 0;

void recvByte(uint8_t byte)
{
    switch(recvState) {
        case REV_STATE_HEAD0:
            if (byte == DF2301Q_UART_MSG_HEAD_LOW)
                recvState = REV_STATE_HEAD1;
            break;
        case REV_STATE_HEAD1:
            if (byte == DF2301Q_UART_MSG_HEAD_HIGH)
                recvState = REV_STATE_LENGTH0;
            else if (byte != DF2301Q_UART_MSG_HEAD_LOW)
                recvState = REV_STATE_HEAD0;
            break;
        case REV_STATE_LENGTH0:
            length = byte;
            recvState = REV_STATE_LENGTH1;
            break;
        case REV_STATE_LENGTH1:
            length |= (byte << 8);
            if (length <= DF2301Q_UART_MSG_DATA_MAX_SIZE)
                recvState = REV_STATE_TYPE;
            else
                recvState = REV_STATE_HEAD0;
            break;
        case REV_STATE_TYPE:
            recvState = REV_STATE_CMD;
            break;
        case REV_STATE_CMD:
            recvState = REV_STATE_SEQ;
            break;
        case REV_STATE_SEQ:
            if (length > 0) {
                dataCount = 0;
                recvState = REV_STATE_DATA;
            } else {
                recvState = REV_STATE_CKSUM0;
            }
            break;
        case REV_STATE_DATA:
            if(dataCount < length)
                packetData[dataCount++] = byte;
            if(dataCount == length)
                recvState = REV_STATE_CKSUM0;
            break;
        case REV_STATE_CKSUM0:
            checksum = byte;
            recvState = REV_STATE_CKSUM1;
            break;
        case REV_STATE_CKSUM1:
            checksum |= (byte << 8);
            recvState = REV_STATE_TAIL;
            break;
        case REV_STATE_TAIL:
            if(byte == DF2301Q_UART_MSG_TAIL) {
                uartCmdId = packetData[0]; // 保存命令ID
            }
            recvState = REV_STATE_HEAD0;
            break;
        default:
            recvState = REV_STATE_HEAD0;
            break;
    }
}

uint8_t getCMDID(void)
{
    uint8_t ret = 0;
    __disable_irq();
    ret = uartCmdId;
    uartCmdId = 0;
    __enable_irq();
    return ret;
}

void USART2_Init(void)
{
    // 使能时钟
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;   // GPIOA 时钟使能
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;  // USART2 时钟使能

    // PA2 -> USART2_TX, PA3 -> USART2_RX
    GPIOA->MODER &= ~((3 << (2*2)) | (3 << (3*2)));
    GPIOA->MODER |=  ((2 << (2*2)) | (2 << (3*2))); // 复用模式

    GPIOA->AFR[0] &= ~((0xF << (2*4)) | (0xF << (3*4)));
    GPIOA->AFR[0] |=  ((7 << (2*4)) | (7 << (3*4))); // AF7=USART2

    // USART2 配置：波特率 115200，APB1=42MHz
    USART2->BRR = 42000000 / 115200;

    USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_RXNEIE; // 使能发送、接收、中断
    USART2->CR1 |= USART_CR1_UE;  // 使能 USART

    NVIC_EnableIRQ(USART2_IRQn);
    NVIC_SetPriority(USART2_IRQn, 1);
}

// 简单的阻塞式串口发送一个字节（用于printf）
void USART2_SendByte(uint8_t ch)
{
    while (!(USART2->SR & USART_SR_TXE)); // 等待发送缓冲区空
    USART2->DR = ch;
    while (!(USART2->SR & USART_SR_TC));  // 等待发送完成
}

// 重定向printf到USART2
int fputc(int ch, FILE *f)
{
    USART2_SendByte((uint8_t)ch);
    return ch;
}

void USART2_IRQHandler(void)
{
    if(USART2->SR & USART_SR_RXNE)
    {
        uint8_t data = USART2->DR;
        recvByte(data);
    }
}

int main(void)
{
    SystemInit();
    USART2_Init();

    while(1)
    {
        uint8_t cmd = getCMDID();
        if(cmd != 0)
        {
            printf("Received Command ID: %d\r\n", cmd);
            switch(cmd)
            {
                case 5:
                    printf("Voice Command 5 detected\r\n");
                    break;
                case 6:
                    printf("Voice Command 6 detected\r\n");
                    break;
                case 7:
                    printf("Voice Command 7 detected\r\n");
                    break;
                default:
                    printf("Unknown Command\r\n");
                    break;
            }
        }
    }
}
