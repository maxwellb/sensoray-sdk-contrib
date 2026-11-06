// Sensoray 2600 demo, adapted for MSYS2 UCRT64 (Windows).
// Author      : Jim Lamberson (original Linux demo.c)
// Copyright   : (C) 2008 Sensoray
// Contributor : Maxwell Bloch (github.com/maxwellb), 2026 — MSYS2 UCRT64 (x86_64-w64-mingw32) port.
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <conio.h>
#include <windows.h>

#include "app2600.h"

#define IP_ADDRESS        "10.10.10.1"
#define MMHANDLE          0
#define MSEC_GATEWAY      100
#define MSEC_COMPORT      100
#define COM_RETRIES       50
#define GATEWAY_RETRIES   50

#define CHAN_WIDTH        0
#define CHAN_FREQ         1
#define CHAN_PWM          2
#define CHAN_ENCODER      3

#define COM_SRC_A         LOGDEV_COM2
#define COM_DST_A         LOGDEV_COM1
#define COM_BR_A          SIO_BR_9600
#define COM_SRC_B         LOGDEV_COM4
#define COM_DST_B         LOGDEV_COM3
#define COM_BR_B          SIO_BR_115200

#define COM_REJECT_IGNORE 0
#define COM_REJECT_EVAL   1

typedef void *HX;

int          iters = 0;
u16          nboards;
u16          IomType[16];
u8           IomStatus[16];
u8           nAouts2608[16];
u16          LinkFlags;
u8           LockFlags;
u8           DinStates[6];
DOUBLE       Ain[16];
u8           RelayStates = 0;
u8           DoutStates[6] = { 0, };
DOUBLE       Aout[MAX_NUM_AOUTS] = { 0, };
u32          Counts[4] = { 0, };
u16          Timestamp[4] = { 0, };

static int  io_exec(HX x);
static void io_control_main(void);
static int  DetectAllIoms(void);
static HX   CreateTransaction(HBD hbd);

int main(void)
{
    u32 faults;

    if ((faults = S26_DriverOpen(1)) != 0)
    {
        printf("DriverOpen() fault: %d\n", (int)faults);
        return 1;
    }

    if ((faults = S26_BoardOpen(MMHANDLE, 0, IP_ADDRESS)) != 0)
    {
        printf("BoardOpen() fault: %d\n", (int)faults);
        S26_DriverClose();
        return 1;
    }

    S26_ResetNetwork(MMHANDLE);

    if (DetectAllIoms())
        io_control_main();

    S26_DriverClose();
    return 0;
}

void ShowErrorInfo(u32 gwerr, u8 *IomStatus)
{
    char errmsg[128];
    int ExtraInfo = gwerr & ~GWERRMASK;

    switch (gwerr & GWERRMASK)
    {
    case GWERR_IOMSPECIFIC:  sprintf(errmsg, "Iom-specific error on iomport %d", ExtraInfo); break;
    case GWERR_BADVALUE:     sprintf(errmsg, "Illegal value for argument %d", ExtraInfo); break;
    case GWERR_IOMCLOSED:    sprintf(errmsg, "Iom is not open"); break;
    case GWERR_IOMERROR:     sprintf(errmsg, "Iom CERR asserted"); break;
    case GWERR_IOMNORESPOND: sprintf(errmsg, "Bad module response from iomport %d", ExtraInfo); break;
    case GWERR_IOMRESET:     sprintf(errmsg, "Module RST asserted"); break;
    case GWERR_IOMTYPE:      sprintf(errmsg, "Action not supported by iom type"); break;
    case GWERR_MMCLOSED:     sprintf(errmsg, "MM is closed"); break;
    case GWERR_MMNORESPOND:  sprintf(errmsg, "MM response timed out"); break;
    case GWERR_PACKETSEND:   sprintf(errmsg, "Failed to send cmd packet"); break;
    case GWERR_TOOLARGE:     sprintf(errmsg, "Command or response packet too large"); break;
    case GWERR_XACTALLOC:    sprintf(errmsg, "Transaction Object allocation problem"); break;
    default:                 sprintf(errmsg, "Unknown error"); break;
    }

    printf("Error: 0x%X (%s), iters = %d.\n", (int)gwerr, errmsg, iters);
}

u32 ComError(u32 gwerr, const char *fname, int evalComReject)
{
    char errmsg[128] = "";

    if (gwerr & GWERRMASK)
    {
        switch (gwerr & GWERRMASK)
        {
        case GWERR_BADVALUE:     sprintf(errmsg, "Illegal value for argument %u", gwerr & ~GWERRMASK); break;
        case GWERR_IOMRESET:     sprintf(errmsg, "Module RST asserted"); break;
        case GWERR_MMCLOSED:     sprintf(errmsg, "MM is closed"); break;
        case GWERR_MMNORESPOND:  sprintf(errmsg, "MM response timed out"); break;
        case GWERR_PACKETSEND:   sprintf(errmsg, "Failed to send cmd packet"); break;
        case GWERR_TOOLARGE:     sprintf(errmsg, "Command or response packet too large"); break;
        case GWERR_XACTALLOC:    sprintf(errmsg, "Transaction Object allocation problem"); break;
        default:                 sprintf(errmsg, "Unknown error"); break;
        }
    }
    else if (gwerr & COM_FRAMINGERROR)  sprintf(errmsg, "Framing error");
    else if (gwerr & COM_PARITYERROR)   sprintf(errmsg, "Parity error");
    else if (gwerr & COM_OVERFLOWERROR) sprintf(errmsg, "Receiver overflow");
    else if ((gwerr & COM_REJECTED) && (evalComReject == COM_REJECT_EVAL))
        sprintf(errmsg, "Command rejected");
    else
        return GWERR_NONE;

    printf("%s() error: 0x%X (%s), iters = %d.\n", fname, gwerr, errmsg, iters);
    return gwerr;
}

int DetectAllIoms(void)
{
    int i;
    u32 faults;

    if ((faults = S26_RegisterAllIoms(MMHANDLE, MSEC_GATEWAY, &nboards, IomType, IomStatus, GATEWAY_RETRIES)) != 0)
    {
        ShowErrorInfo(faults, IomStatus);
        return 0;
    }

    printf("DETECTED IOM'S:\n");
    for (i = 0; i < 16; i++)
        if (IomType[i])
            printf(" port %2.2d: %4.4d\n", i, IomType[i]);

    return 1;
}

static void sched_io(HX x)
{
    int chan;
    u8 i;

    S26_Sched2601_GetLinkStatus(x, &LinkFlags);
    S26_Sched2601_GetInterlocks(x, &LockFlags);

    for (i = 0; i < 16; i++)
    {
        switch (IomType[i])
        {
        case 2608:
            S26_Sched2608_GetCalData(x, i, 0);
            S26_Sched2608_GetAins(x, i, Ain, ADC_INTEGRATED);
            for (chan = 0; chan < (int)nAouts2608[i]; chan++)
                S26_Sched2608_SetAout(x, i, (u8)chan, Aout[chan]);
            break;

        case 2610:
            S26_Sched2610_SetOutputs(x, i, DoutStates);
            S26_Sched2610_GetInputs(x, i, DinStates);
            break;

        case 2620:
            S26_Sched2620_SetControlReg(x, i, CHAN_PWM, 2);
            S26_Sched2620_SetControlReg(x, i, CHAN_ENCODER, 2);
            for (chan = 0; chan < 4; chan++)
                S26_Sched2620_GetCounts(x, i, (u8)chan, &Counts[chan], &Timestamp[chan]);
            break;

        case 2650:
        case 2652:
            S26_Sched2650_SetOutputs(x, i, &RelayStates);
            break;
        }
    }
}

static int SerialInit(u8 ComSrc, u8 ComDst, u16 BaudRate)
{
    u32 comstatus;

    comstatus = S26_ComSetMode(MMHANDLE, ComSrc, BaudRate,
        SIO_PHY_RS232 | SIO_PARITY_NONE | SIO_DATA_8 | SIO_STOP_1 | SIO_FLOW_OFF,
        SIO_LED_TRANSMIT, MSEC_COMPORT, COM_RETRIES);
    if (ComError(comstatus, "S26_ComSetMode", COM_REJECT_EVAL)) return 1;

    comstatus = S26_ComOpen(MMHANDLE, ComSrc, MSEC_COMPORT, COM_RETRIES);
    if (ComError(comstatus, "S26_ComOpen", COM_REJECT_EVAL)) return 1;

    comstatus = S26_ComSetMode(MMHANDLE, ComDst, BaudRate,
        SIO_PHY_RS232 | SIO_PARITY_NONE | SIO_DATA_8 | SIO_STOP_1 | SIO_FLOW_OFF,
        SIO_LED_RECEIVE, MSEC_COMPORT, COM_RETRIES);
    if (ComError(comstatus, "S26_ComSetMode", COM_REJECT_EVAL)) return 1;

    comstatus = S26_ComOpen(MMHANDLE, ComDst, MSEC_COMPORT, COM_RETRIES);
    if (ComError(comstatus, "S26_ComOpen", COM_REJECT_EVAL)) return 1;

    return 0;
}

static int SerialIo(u8 ComSrc, u8 ComDst)
{
    static int totalSent = 0;
    int msglen;
    char SndBuf[1024];
    char RcvBuf[1024];
    u16 BufLen;
    u32 comstatus;

    sprintf(SndBuf, "12345678901234567890123456:%d\n", iters);
    msglen = strlen(SndBuf);

    comstatus = S26_ComSend(MMHANDLE, ComSrc, (u8 *)SndBuf, (u16)msglen, MSEC_COMPORT, COM_RETRIES);
    if (ComError(comstatus, "S26_ComSend", COM_REJECT_IGNORE))
    {
        printf("TotalSent = %d\n", totalSent);
        return 1;
    }
    totalSent += msglen;

    BufLen = sizeof(RcvBuf);
    comstatus = S26_ComReceive(MMHANDLE, ComDst, (u8 *)RcvBuf, &BufLen, MSEC_COMPORT, COM_RETRIES);
    if (ComError(comstatus, "S26_ComReceive", COM_REJECT_EVAL))
    {
        printf("TotalSent = %d\n", totalSent);
        return 1;
    }
    RcvBuf[BufLen] = 0;

    return 0;
}

static int io_control_loop(void)
{
    HX x;
    u8 chan;
    DWORD tStart, tEnd, tDiff, tMax = 0;

    for (;;)
    {
        RelayStates++;
        if (++DoutStates[0] == 0)
        if (++DoutStates[1] == 0)
        if (++DoutStates[2] == 0)
        if (++DoutStates[3] == 0)
        if (++DoutStates[4] == 0)
        ++DoutStates[5];

        for (chan = 0; chan < MAX_NUM_AOUTS; chan++)
            Aout[chan] = (double)(chan + 1);

        if (SerialIo(COM_SRC_A, COM_DST_A)) return iters;
        if (SerialIo(COM_SRC_B, COM_DST_B)) return iters;

        x = CreateTransaction(MMHANDLE);
        sched_io(x);

        tStart = GetTickCount();
        if (io_exec(x))
        {
            printf("Terminating i/o control loop.\n");
            break;
        }
        tEnd = GetTickCount();
        tDiff = tEnd - tStart;
        if (tDiff > tMax) tMax = tDiff;

        iters++;

        if (_kbhit())
        {
            _getch();
            break;
        }
    }

    printf("Worst-case I/O time (msec):  %lu\n", tMax);
    return iters;
}

static void io_control_main(void)
{
    u8 i;
    int j;
    HX x;
    time_t StartTime;
    double tElapsed;

    const u8 ain_types[] = {
        V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE,
        V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE, V_10_TYPE
    };

    SerialInit(COM_SRC_A, COM_DST_A, COM_BR_A);
    SerialInit(COM_SRC_B, COM_DST_B, COM_BR_B);

    x = CreateTransaction(MMHANDLE);

    for (i = 0; i < 16; i++)
    {
        switch (IomType[i])
        {
        case 2608:
            S26_Sched2608_ReadEeprom(x, i, 0, &nAouts2608[i]);
            S26_Sched2608_SetLineFreq(x, i, LINEFREQ_60HZ);
            S26_Sched2608_SetAinTypes(x, i, ain_types);
            break;

        case 2620:
            S26_Sched2620_SetCommonControl(x, i, 1000, 3);
            S26_Sched2620_SetPreload(x, i, CHAN_PWM, 1, 99);
            S26_Sched2620_SetPreload(x, i, CHAN_PWM, 0, 4899);
            S26_Sched2620_SetModePwmGen(x, i, CHAN_PWM, 0);
            S26_Sched2620_SetModeFreqMeas(x, i, CHAN_FREQ, 1);
            S26_Sched2620_SetModePulseMeas(x, i, CHAN_WIDTH, 0);
            S26_Sched2620_SetModeEncoder(x, i, CHAN_ENCODER, 0, 0, 3);
            break;
        }
    }

    if (io_exec(x)) return;

    printf("Running main control loop\nHit any key to terminate\n");
    StartTime = time(NULL);
    iters = io_control_loop();
    tElapsed = difftime(time(NULL), StartTime);

    for (i = 0; i < 16; i++)
    {
        switch (IomType[i])
        {
        case 2608:
            printf("AIN states:\n");
            for (j = 0; j < 16; j++)
                printf(" %8f\n", Ain[j]);
            break;
        case 2610:
            printf("DIN states:");
            for (j = 0; j < 6; j++)
                printf(" %2.2hhX", DinStates[j]);
            printf("\n");
            break;
        case 2620:
            printf("Counter states:");
            for (j = 0; j < 4; j++)
                printf("%d:%8.8X ", j, Counts[j]);
            printf("\n");
            break;
        }
    }

    printf("Control loop cycles:    %d\n", iters);
    printf("Elapsed time (seconds): %u\n", (u32)tElapsed);
    printf("Average I/O cycle time (msec):  %.2f\n", tElapsed / (double)iters * 1000.0);
}

HX CreateTransaction(HBD hbd)
{
    HX x = S26_SchedOpen(hbd, GATEWAY_RETRIES);
    if (x == 0)
        printf("Error: S26_SchedOpen() failed to allocate a transaction object.\n");
    return x;
}

int io_exec(HX x)
{
    GWERR err;
    if ((err = S26_SchedExecute(x, MSEC_GATEWAY, IomStatus)) != 0)
        ShowErrorInfo(err, IomStatus);
    return (int)err;
}
