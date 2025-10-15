#include <arpa/inet.h>
#include <arpa/nameser.h>
#include <arpa/nameser_compat.h>
#include <netinet/in.h>
#include <resolv.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>

void print_rr(const unsigned char *begin, const unsigned char *end, ns_rr rr) {
  int type = ns_rr_type(rr);

  // A
  if (type == T_A && ns_rr_rdlen(rr) == 4) {
    char ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, ns_rr_rdata(rr), ip, sizeof(ip));
    printf("  %s A     %s\n", ns_rr_name(rr), ip);
  }

  // AAAA
  else if (type == T_AAAA && ns_rr_rdlen(rr) == 16) {
    char ip[INET6_ADDRSTRLEN];
    inet_ntop(AF_INET6, ns_rr_rdata(rr), ip, sizeof(ip));
    printf("  %s AAAA  %s\n", ns_rr_name(rr), ip);
  }

  // TXT
  else if (type == T_TXT) {
    printf("  %s TXT   ", ns_rr_name(rr));
    int len = ns_rr_rdlen(rr);
    const unsigned char *txt = ns_rr_rdata(rr);
    int c;
    while ((c = *txt++) && c < len) {
      fwrite(txt, 1, c, stdout);
      txt += c;
      len -= c + 1;
    }
    printf("\n");
  }

  // CNAME
  else if (type == T_CNAME) {
    char name[256];
    ns_name_uncompress(begin, end, ns_rr_rdata(rr), name, sizeof(name));
    printf("  %s CNAME %s\n", ns_rr_name(rr), name);
  }

  // NS
  else if (type == T_NS) {
    char name[256];
    ns_name_uncompress(begin, end, ns_rr_rdata(rr), name, sizeof(name));
    printf("  %s NS    %s\n", ns_rr_name(rr), name);
  }
}

int main() {
  unsigned char buf[512];
  int msglen;

  // construct DNS query
  msglen = res_nmkquery(&_res,
                        QUERY,             // query
                        "www.example.com", // domain
                        C_IN,              // query class = IN
                        T_A,               // query type = A
                        NULL, 0,           // extra data
                        NULL,              // unused
                        buf,               // buffer ptr
                        sizeof(buf)        // buffer size
  );

  if (msglen < 0) {
    perror("res_nmkquery");
    return 1;
  }

  // create UDP socket
  struct sockaddr_in server;
  int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
  if (sockfd < 0) {
    perror("socket");
    return 1;
  }

  // set server to a.root-servers.net
  server.sin_family = AF_INET;
  server.sin_port = htons(53);
  // a.root-servers.net
  inet_pton(AF_INET, "198.41.0.4", &server.sin_addr);

  // send datagram
  if (sendto(sockfd, buf, msglen, 0, (struct sockaddr *)&server,
             sizeof(server)) < 0) {
    perror("sendto");
    return 1;
  }

  // recv datagram
  socklen_t slen = sizeof(server);
  int recvlen =
      recvfrom(sockfd, buf, sizeof(buf), 0, (struct sockaddr *)&server, &slen);
  if (recvlen < 0) {
    perror("recvfrom");
    return 1;
  }

  printf("recvfrom: %d bytes\n", recvlen);

  // parse DNS response
  ns_msg nsmsg;
  ns_rr rr;
  if (ns_initparse(buf, recvlen, &nsmsg) < 0) {
    perror("ns_initparse");
    return 1;
  }

  // Answer Section
  int an_count = ns_msg_count(nsmsg, ns_s_an);
  printf("%d records in Answer Section:\n", an_count);
  for (int i = 0; i < an_count; i++) {
    if (ns_parserr(&nsmsg, ns_s_an, i, &rr) == 0) {
      print_rr(buf, buf + recvlen, rr);
    }
  }

  // Authority Section
  int ns_count = ns_msg_count(nsmsg, ns_s_ns);
  printf("%d records in Authority Section:\n", ns_count);
  for (int i = 0; i < ns_count; i++) {
    if (ns_parserr(&nsmsg, ns_s_ns, i, &rr) == 0) {
      print_rr(buf, buf + recvlen, rr);
    }
  }

  // Additional Section
  int ar_count = ns_msg_count(nsmsg, ns_s_ar);
  printf("%d records in Additional Section:\n", ar_count);
  for (int i = 0; i < ar_count; i++) {
    if (ns_parserr(&nsmsg, ns_s_ar, i, &rr) == 0) {
      print_rr(buf, buf + recvlen, rr);
    }
  }

  close(sockfd);
  return 0;
}
