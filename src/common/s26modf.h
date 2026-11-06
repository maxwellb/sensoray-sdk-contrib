///////////////////////////////////////////////////////////////////////////////////////////////
// Module    : s26modf.h	
// Function  : Definitions shared by s26mod.c and s26core.c
// Target OS : Any (operating system independent)
// Author    : Jim Lamberson
// Copyright : (C) 2008 Sensoray
///////////////////////////////////////////////////////////////////////////////////////////////

#ifndef _INC_S26MODF_H_
#define _INC_S26MODF_H_

// Constants
#define S26_INVALID_SOCKET              ((S26_SOCKET)0)             // Invalid socket handle: socket has not been created.
#define S26_INVALID_THREAD              ((S26_THREAD)0)             // Invalid socket handle: socket has not been created.
#define S26_INVALID_CRITICALSECTION     ((S26_CRITICALSECTION)0)    // Invalid critical section handle: cs has not been created.
#define S26_INVALID_SEMAPHORE           ((S26_SEMAPHORE)0)          // Invalid semaphore handle: semaphore has not been created.

#define SEM_SIGNALED        1
#define SEM_TIMEOUT         0

#define THREAD_SIGNALED     1
#define THREAD_TIMEOUT      0

// Types
typedef THREAD_RTNTYPE (* S26_THREADPROC)(void *);                  // Thread function.

// Prototypes of functions implemented in s26mod.c
int                 S26MOD_BindSocket               (S26_SOCKET hSock, u32 nordClientIPAdrs);
int                 S26MOD_CloseNetwork             (void);
void                S26MOD_CloseSocket              (S26_SOCKET hSock);
S26_SOCKET          S26MOD_CreateSocket             (void);
void                S26MOD_CriticalSectionBegin     (S26_CRITICALSECTION cs);
S26_CRITICALSECTION S26MOD_CriticalSectionCreate    (void);
void                S26MOD_CriticalSectionDestroy   (S26_CRITICALSECTION cs);
void                S26MOD_CriticalSectionEnd       (S26_CRITICALSECTION cs);
void				S26MOD_SemaphorePost            (S26_SEMAPHORE s);
S26_SEMAPHORE       S26MOD_SemaphoreCreate          (u32 capacity, u32 initcount);
void                S26MOD_SemaphoreDestroy         (S26_SEMAPHORE s);
int                 S26MOD_SemaphorePend            (S26_SEMAPHORE s, u32 tmax);            // wait on semaphore. returns SEM_SIGNALED | SEM_SIGNALED
S26_THREAD          S26MOD_ThreadCreate             (S26_THREADPROC proc, void *param);
int                 S26MOD_ThreadWait               (S26_THREAD, u32 tmax);                 // wait for thread termination. returns THREAD_SIGNALED | THREAD_TIMEOUT
void                S26MOD_ThreadDisconnect         (S26_THREAD t);
u32                 S26MOD_CurrentTime              (void);
u32                 S26MOD_inet_addr                (const char *dot_adrs);
int                 S26MOD_IsPacketRcvd             (S26_SOCKET hSock, u32 msec);
int                 S26MOD_OpenNetwork              (u32 MaxNumSockets);
u16                 S26MOD_RecvPacket               (S26_SOCKET hSock, u8 *pBuf, u16 BufLen);
int                 S26MOD_SendPacket               (S26_SOCKET hSock, u32 MMAdrs, u16 MMPort, const u8 *pCmd, u16 CmdLen, u32 msec);

S26_SOCKET          S26MOD_CreateSocketForPing(void);
int S26MOD_SendPing(S26_SOCKET hSock, u32 MMAdrs, const u8 *pCmd, u16 CmdLen, u32 msec );

#endif	// ifdef _INC_S26MODF_H_
