//////////////////////////////////////////////////////////////////////////
// Module    : s26mod.c
// Function  : OS-dependent API library (top level) for 2600 core
// Target OS : MSYS2 UCRT64 (Windows, Win32 sockets + Win32 threads), x86_64-w64-mingw32
// Author    : Jim Lamberson (adapted for MSYS2-UCRT64)
// Copyright : (C) 2004 Sensoray
// Contributor: Maxwell Bloch (github.com/maxwellb), 2026 — MSYS2 UCRT64 (x86_64-w64-mingw32) port.
//////////////////////////////////////////////////////////////////////////


#include "s26app.h"
#include "s26mod.h"
#include "s26modf.h"


// Helper: widen a stored socket handle back to a Winsock SOCKET.
// The core stores S26_SOCKET as a u32; Winsock SOCKET is UINT_PTR.
#define SOCK(h) ((SOCKET)(h))


////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////  EXPORTED LIBRARY FUNCTIONS ///////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////


///////////////////////////////////////////////////////////////////
// Convert IP dotted address to network byte ordered IP address.
// Imports:
//  dot_adrs : dotted IP address.
// Returns binary IP address in network byte order.

u32 S26MOD_inet_addr( const char *dot_adrs )
{
	return (u32)inet_addr( dot_adrs );
}

/////////////////////////////////////////////////////////////////////////
// Open the socket interface.
// Imports:
//	MaxNumSockets : number of sockets required for all MMs in the system.
// Returns zero if successful.

int S26MOD_OpenNetwork( u32 MaxNumSockets )
{
	WSADATA wsaData;
	(void)MaxNumSockets;
	return ( WSAStartup( MAKEWORD(2, 2), &wsaData ) == 0 ) ? 0 : -1;
}

//////////////////////////////////
// Close the socket interface.

int S26MOD_CloseNetwork()
{
	WSACleanup();
	return 0;	// success
}

//////////////////////////////////////////////////////////////////////////////////////////////////////
// Bind a socket to a network interface card.  In a multihomed host, specify the IP address of the
// desired network interface card to bind to a specific NIC.  Zero may be specified as the target
// IP address, in which case the socket will be bound to the host's default NIC.
// Imports:
//  hSock          : handle to socket.
//  nordClientIPAdrs : IP address, in network byte order, of client's interface (0 = default).
// Returns True if successful.

int S26MOD_BindSocket( S26_SOCKET hSock, u32 nordClientIPAdrs )
{
	struct sockaddr_in ClientAddr;
	memset( &ClientAddr, 0, sizeof(ClientAddr) );
	ClientAddr.sin_family			= AF_INET;
	ClientAddr.sin_addr.s_addr		= nordClientIPAdrs;
	ClientAddr.sin_port				= 0;

	return ( bind( SOCK(hSock), (struct sockaddr *)&ClientAddr, sizeof(ClientAddr) ) == 0 );
}

////////////////////////////////////////////////////////////////////////////////////////////////////
// Transmit a UDP packet to the specified socket and IP port.  The calling thread is blocked until
// the packet is successfully sent or a timeout occurs.
// Imports:
//   hSock	: handle to open socket.
//   MMAdrs	: target IP address in network byte order.
//   MMPort	: target IP port in network byte order.
//   pCmd	: buffer that contains UDP payload to be transmitted.
//   CmdLen	: size of Cmd buffer.
//   msec	: maximum time to wait for socket to become ready to transmit.
// Returns non-zero value if successful.

int S26MOD_SendPacket( S26_SOCKET hSock, u32 MMAdrs, u16 MMPort, const u8 *pCmd, u16 CmdLen, u32 msec )
{
	int rtnval = FALSE;

	struct sockaddr_in	ServerAddr;
	fd_set				EnabledFDSet;
	struct timeval		TimeValue;

	TimeValue.tv_sec	= (long)(msec / 1000);
	TimeValue.tv_usec	= (long)((msec % 1000) * 1000);

	FD_ZERO( &EnabledFDSet );
	FD_SET( SOCK(hSock), &EnabledFDSet );

	if ( select( 0, NULL, &EnabledFDSet, NULL, &TimeValue ) == 1 )
	{
		memset( &ServerAddr, 0, sizeof(ServerAddr) );
		ServerAddr.sin_port			= htons( MMPort );
		ServerAddr.sin_family		= AF_INET;
		ServerAddr.sin_addr.s_addr	= MMAdrs;

		rtnval = ( sendto( SOCK(hSock), (const char *)pCmd, CmdLen, 0, (struct sockaddr *)&ServerAddr, sizeof(ServerAddr) ) == CmdLen );
	}

	return rtnval;
}

int S26MOD_SendPing( S26_SOCKET hSock, u32 MMAdrs, const u8 *pCmd, u16 CmdLen, u32 msec )
{
	// Raw ICMP ping is not used by the 2600 core; provide a non-functional stub.
	(void)hSock; (void)MMAdrs; (void)pCmd; (void)CmdLen; (void)msec;
	return FALSE;
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////
// Receive a UDP datagram from the specified socket and IP port.  It is assumed that a packet has already
// been received; this should be verified by calling S26MOD_IsPacketRcvd() before calling this function.
// Imports:
//   hSock   : handle to socket.
//   pBuf    : buffer that is to receive the datagram.
//   BufLen  : size of receive buffer.
// Returns byte count of the received datagram.

u16 S26MOD_RecvPacket( S26_SOCKET hSock, u8 *pBuf, u16 BufLen )
{
	int rtnval = recvfrom( SOCK(hSock), (char *)pBuf, (int)BufLen, 0, 0, 0 );
	return ( rtnval == SOCKET_ERROR ) ? S26_INVALID_SOCKET : (u16)rtnval;
}

//////////////////////////////////////////////////////////////////
// Determine whether a packet has been received.
// Imports:
//   hSock : handle to socket.
//   msec  : maximum time, in milliseconds, to wait for packet.
// Returns TRUE if received, FALSE if not received.

int S26MOD_IsPacketRcvd( S26_SOCKET hSock, u32 msec )
{
	fd_set	EnabledFDSet;
	struct timeval	TimeValue;

	TimeValue.tv_sec	= (long)(msec / 1000);
	TimeValue.tv_usec	= (long)((msec % 1000) * 1000);

	FD_ZERO( &EnabledFDSet );
	FD_SET( SOCK(hSock), &EnabledFDSet );

	return ( select( 0, &EnabledFDSet, NULL, NULL, &TimeValue ) == 1 );
}

////////////////////////////////////////////////////////////////
// Create a socket.
// Returns socket handle if successful, otherwise return 0.

S26_SOCKET S26MOD_CreateSocket( void )
{
	SOCKET hSocket = socket( PF_INET, SOCK_DGRAM, IPPROTO_UDP );
	return ( hSocket == INVALID_SOCKET ) ? S26_INVALID_SOCKET : (S26_SOCKET)hSocket;
}

S26_SOCKET S26MOD_CreateSocketForPing( void )
{
	return S26_INVALID_SOCKET;	// raw ICMP ping not used by core.
}

////////////////////
// Close a socket.
// Imports:
//   hSock : handle to socket.

void S26MOD_CloseSocket( S26_SOCKET hSock )
{
	closesocket( SOCK(hSock) );
}

////////////////////////////////////////////////////////////////////////////////////////////////////////
// Get the current time expressed in milliseconds since system startup (wraps around after 2^32 msec).

u32 S26MOD_CurrentTime( void )
{
	return (u32)GetTickCount();
}


////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////  CRITICAL SECTION FUNCTIONS  ////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////


/////////////////////////////////////////////////////////
// Create critical section object and return its handle.
// Returns zero upon fail.

S26_CRITICALSECTION S26MOD_CriticalSectionCreate( void )
{
	S26_CRITICALSECTION cs = malloc( sizeof( CRITICAL_SECTION ) );
	if ( cs != NULL )
		InitializeCriticalSection( cs );
	else
		cs = S26_INVALID_CRITICALSECTION;
	return cs;
}

///////////////////////////////////////////////////
// Destroy critical section access control object.

void S26MOD_CriticalSectionDestroy( S26_CRITICALSECTION cs )
{
	if ( cs != S26_INVALID_CRITICALSECTION ) {
		DeleteCriticalSection( cs );
		free( cs );
	}
}

///////////////////////////////////////////////
// Begin critical section.

void S26MOD_CriticalSectionBegin( S26_CRITICALSECTION cs )
{
	EnterCriticalSection( cs );
}

/////////////////////////////////////////
// Leave critical section.

void S26MOD_CriticalSectionEnd( S26_CRITICALSECTION cs )
{
	LeaveCriticalSection( cs );
}

//////////////////////////////////////////////////////////////////////////
// Thread functions.

// Thread context passed to the Win32 thread trampoline (Win32 thread proc
// uses __stdcall and DWORD return, while the core uses void* (void*)).
typedef struct {
	S26_THREADPROC proc;
	void *param;
} THREAD_CTX;

static DWORD WINAPI ThreadStub( void *p )
{
	THREAD_CTX *c = (THREAD_CTX *)p;
	S26_THREADPROC proc = c->proc;
	void *param = c->param;
	free( c );
	proc( param );
	return 0;
}

// Create a thread.
S26_THREAD S26MOD_ThreadCreate(S26_THREADPROC proc, void *param)
{
	THREAD_CTX *c = malloc( sizeof(THREAD_CTX) );
	if ( c == NULL )
		return S26_INVALID_THREAD;
	c->proc = proc;
	c->param = param;

	HANDLE h = CreateThread( NULL, 0, ThreadStub, c, 0, NULL );
	if ( h == NULL ) {
		free( c );
		return S26_INVALID_THREAD;
	}
	return h;
}

void S26MOD_ThreadDisconnect(S26_THREAD t)
{
	if ( t != S26_INVALID_THREAD )
		CloseHandle( t );
}

// Wait for thread termination. Returns THREAD_SIGNALED | THREAD_TIMEOUT
int S26MOD_ThreadWait(S26_THREAD t, u32 tmax)
{
	DWORD r = WaitForSingleObject( t, tmax );
	return ( r == WAIT_OBJECT_0 ) ? THREAD_SIGNALED : THREAD_TIMEOUT;
}

//////////////////////////////////////////////////////////////////////////
// Semaphore functions.

S26_SEMAPHORE S26MOD_SemaphoreCreate( u32 capacity, u32 initcount )
{
	HANDLE h = CreateSemaphoreA( NULL, (LONG)initcount, (LONG)capacity, NULL );
	return ( h == NULL ) ? S26_INVALID_SEMAPHORE : h;
}

void S26MOD_SemaphoreDestroy( S26_SEMAPHORE s )
{
	if ( s != S26_INVALID_SEMAPHORE )
		CloseHandle( s );
}

void S26MOD_SemaphorePost( S26_SEMAPHORE s )
{
	ReleaseSemaphore( s, 1, NULL );
}

// Wait on semaphore. Returns SEM_SIGNALED | SEM_TIMEOUT
int S26MOD_SemaphorePend( S26_SEMAPHORE s, u32 tmax )
{
	DWORD r = WaitForSingleObject( s, tmax );
	return ( r == WAIT_OBJECT_0 ) ? SEM_SIGNALED : SEM_TIMEOUT;
}
