#!/bin/bash
killall chrome

google-chrome \
    --enable-quic \
    --origin-to-force-quic-on=csc466-router.baxtergroup.io:443 \
    --user-data-dir=/tmp/random12 \
    --remote-debugging-port=9221 \
    --disable-gpu \
    --no-first-run \
    --disable-background-networking \
    --disable-client-side-phishing-detection \
    --disable-component-update \
    --disable-default-apps \
    --disable-hang-monitor \
    --disable-popup-blocking \
    --disable-prompt-on-repost \
    --disable-sync \
    --disable-web-resources \
    --metrics-recording-only \
    --password-store=basic \
    --safebrowsing-disable-auto-update \
    --use-mock-keychain \
    --enable-benchmarking \
    --enable-net-benchmarking \
    https://csc466-router.baxtergroup.io/index.html&

google-chrome \
    --user-data-dir=/tmp/random13 \
    --remote-debugging-port=9220 \
    --disable-gpu \
    --no-first-run \
    --disable-background-networking \
    --disable-client-side-phishing-detection \
    --disable-component-update \
    --disable-default-apps \
    --disable-hang-monitor \
    --disable-popup-blocking \
    --disable-prompt-on-repost \
    --disable-sync \
    --disable-web-resources \
    --metrics-recording-only \
    --password-store=basic \
    --safebrowsing-disable-auto-update \
    --use-mock-keychain \
    --enable-benchmarking \
    --enable-net-benchmarking \
    https://csc466-router.baxtergroup.io/index.html&
