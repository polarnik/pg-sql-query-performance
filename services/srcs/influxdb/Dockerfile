# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Dockerfile                                         :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: kallard <kallard@student.21-school.ru>     +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2020/10/13 14:58:02 by kallard           #+#    #+#              #
#    Updated: 2020/10/26 21:48:18 by kallard          ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

FROM alpine:latest

LABEL maintainer="kallard@student.21-school.ru"

RUN apk update && apk add influxdb

EXPOSE 8086

CMD ["influxd", "run", "-config", "/etc/influxdb.conf"]
