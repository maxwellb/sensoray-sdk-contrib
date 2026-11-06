/////////////////////////////////////////////////////////////////////////////
// Module    : s26mod.h
// Function  : 2600 declarations shared by mod/core
// Target OS : MSYS2 UCRT64 (Windows), x86_64-w64-mingw32
// Author    : Jim Lamberson (adapted for MSYS2-UCRT64)
// Copyright : (C) 2008 Sensoray
// Contributor: Maxwell Bloch (github.com/maxwellb), 2026 — MSYS2 UCRT64 (x86_64-w64-mingw32) port.
/////////////////////////////////////////////////////////////////////////////

#ifndef _INC_S26MOD_H_
#define _INC_S26MOD_H_

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include "app2600.h"

// Constants.
#define FALSE		0
#define TRUE		1

#define INFINITE_WAIT       0xFFFFFFFF

// Types.
typedef u32                 S26_SOCKET;             // Winsock SOCKET is a u32-sized handle.
typedef HANDLE              S26_THREAD;
typedef HANDLE              S26_SEMAPHORE;
typedef CRITICAL_SECTION    *S26_CRITICALSECTION;
typedef void                *THREAD_RTNTYPE;

#endif	// ifdef _INC_S26MOD_H_
